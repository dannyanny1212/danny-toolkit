"""
Tests voor NeuralBus - Pub/Sub Event Systeem.

Voer uit: python test_neural_bus.py
"""

import os
import sys
import threading
import time

# Windows UTF-8
sys.stdout.reconfigure(encoding="utf-8")

# Test-mode env
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")
os.environ.setdefault("DANNY_TEST_MODE", "1")
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

# Reset singleton voor elke test
import danny_toolkit.core.neural_bus as bus_module

geslaagd = 0
mislukt = 0
checks = 0


def check(naam, conditie):
    """Verificatie helper."""
    global geslaagd, mislukt, checks
    checks += 1
    if conditie:
        geslaagd += 1
        print(f"  [OK] {naam}")
    else:
        mislukt += 1
        print(f"  [X]  {naam}")


def fresh_bus():
    """Maak een schone bus voor elke test."""
    bus_module._bus_instance = None
    return bus_module.get_bus()


def test_singleton():
    """Test dat get_bus() altijd dezelfde instantie teruggeeft."""
    print("\n=== Test 1: Singleton ===")
    bus1 = fresh_bus()
    bus2 = bus_module.get_bus()
    check("Zelfde instantie", bus1 is bus2)


def test_publish_subscribe():
    """Test basis publish/subscribe flow."""
    print("\n=== Test 2: Publish/Subscribe ===")
    bus = fresh_bus()
    ontvangen = []

    def handler(event):
        ontvangen.append(event)

    bus.subscribe("test_event", handler)
    bus.publish("test_event", {"waarde": 42}, bron="test")

    check("Event ontvangen", len(ontvangen) == 1)
    check("Event type correct", ontvangen[0].event_type == "test_event")
    check("Data correct", ontvangen[0].data["waarde"] == 42)
    check("Bron correct", ontvangen[0].bron == "test")
    check("Timestamp aanwezig", ontvangen[0].timestamp is not None)


def test_meerdere_subscribers():
    """Test meerdere subscribers op hetzelfde event type."""
    print("\n=== Test 3: Meerdere Subscribers ===")
    bus = fresh_bus()
    resultaten = {"a": 0, "b": 0}

    def handler_a(event):
        resultaten["a"] += 1

    def handler_b(event):
        resultaten["b"] += 1

    bus.subscribe("shared_event", handler_a)
    bus.subscribe("shared_event", handler_b)
    bus.publish("shared_event", {}, bron="test")

    check("Handler A ontvangen", resultaten["a"] == 1)
    check("Handler B ontvangen", resultaten["b"] == 1)


def test_type_isolatie():
    """Test dat events alleen naar de juiste subscribers gaan."""
    print("\n=== Test 4: Type Isolatie ===")
    bus = fresh_bus()
    ontvangen_a = []
    ontvangen_b = []

    bus.subscribe("type_a", lambda e: ontvangen_a.append(e))
    bus.subscribe("type_b", lambda e: ontvangen_b.append(e))

    bus.publish("type_a", {"x": 1}, bron="test")

    check("Type A ontvangt", len(ontvangen_a) == 1)
    check("Type B ontvangt niet", len(ontvangen_b) == 0)


def test_wildcard_subscriber():
    """Test wildcard (*) subscriber ontvangt alle events."""
    print("\n=== Test 5: Wildcard Subscriber ===")
    bus = fresh_bus()
    alle_events = []

    bus.subscribe("*", lambda e: alle_events.append(e))

    bus.publish("event_x", {"a": 1}, bron="test")
    bus.publish("event_y", {"b": 2}, bron="test")

    check("Alle events ontvangen", len(alle_events) == 2)
    check("Eerste event correct", alle_events[0].event_type == "event_x")
    check("Tweede event correct", alle_events[1].event_type == "event_y")


def test_unsubscribe():
    """Test dat unsubscribe werkt."""
    print("\n=== Test 6: Unsubscribe ===")
    bus = fresh_bus()
    teller = [0]

    def handler(event):
        teller[0] += 1

    bus.subscribe("test_event", handler)
    bus.publish("test_event", {}, bron="test")
    check("Voor unsubscribe: ontvangen", teller[0] == 1)

    bus.unsubscribe("test_event", handler)
    bus.publish("test_event", {}, bron="test")
    check("Na unsubscribe: niet meer ontvangen", teller[0] == 1)


def test_history():
    """Test event history."""
    print("\n=== Test 7: History ===")
    bus = fresh_bus()

    for i in range(5):
        bus.publish("hist_event", {"nr": i}, bron="test")

    history = bus.get_history("hist_event", count=3)
    check("History beperkt tot count", len(history) == 3)
    check("Nieuwste eerst", history[0].data["nr"] == 4)
    check("Oudste laatst", history[2].data["nr"] == 2)

    latest = bus.get_latest("hist_event")
    check("get_latest correct", latest.data["nr"] == 4)

    check("Geen history voor onbekend type",
          bus.get_latest("onbekend") is None)


def test_history_bron_filter():
    """Test history filtering op bron."""
    print("\n=== Test 8: History Bron Filter ===")
    bus = fresh_bus()

    bus.publish("mixed_event", {"v": 1}, bron="app_a")
    bus.publish("mixed_event", {"v": 2}, bron="app_b")
    bus.publish("mixed_event", {"v": 3}, bron="app_a")

    only_a = bus.get_history("mixed_event", bron="app_a")
    check("Gefilterd op bron A", len(only_a) == 2)
    check("Bron A data correct", all(e.bron == "app_a" for e in only_a))


def test_history_ringbuffer():
    """Test dat history niet onbegrensd groeit."""
    print("\n=== Test 9: History Ringbuffer ===")
    bus = fresh_bus()

    for i in range(150):
        bus.publish("overflow_event", {"nr": i}, bron="test")

    history = bus.get_history("overflow_event", count=200)
    check("History begrensd op MAX_HISTORY",
          len(history) <= bus._MAX_HISTORY)


def test_get_context():
    """Test cross-app context ophalen."""
    print("\n=== Test 10: Cross-App Context ===")
    bus = fresh_bus()

    bus.publish("weather_update", {"temp": 12, "stad": "Amsterdam"},
                bron="weer_agent")
    bus.publish("health_status_change", {"calorieen": 600},
                bron="fitness_tracker")

    ctx = bus.get_context()
    check("Context bevat weather", "weather_update" in ctx)
    check("Context bevat health", "health_status_change" in ctx)

    # Filter op specifiek type
    ctx_weer = bus.get_context(["weather_update"])
    check("Gefilterde context", "weather_update" in ctx_weer)
    check("Andere types uitgesloten",
          "health_status_change" not in ctx_weer)


def test_event_to_dict():
    """Test BusEvent serialisatie."""
    print("\n=== Test 11: Event Serialisatie ===")
    bus = fresh_bus()

    bus.publish("ser_event", {"key": "value"}, bron="test")
    event = bus.get_latest("ser_event")
    d = event.to_dict()

    check("Dict heeft event_type", d["event_type"] == "ser_event")
    check("Dict heeft data", d["data"]["key"] == "value")
    check("Dict heeft bron", d["bron"] == "test")
    check("Dict heeft timestamp", "timestamp" in d)


def test_statistieken():
    """Test bus statistieken."""
    print("\n=== Test 12: Statistieken ===")
    bus = fresh_bus()

    bus.subscribe("stat_event", lambda e: None)
    bus.publish("stat_event", {}, bron="test")
    bus.publish("stat_event", {}, bron="test")

    stats = bus.statistieken()
    check("Subscribers geteld", stats["subscribers"] >= 1)
    check("Events gepubliceerd", stats["events_gepubliceerd"] == 2)
    check("Events afgeleverd", stats["events_afgeleverd"] == 2)
    check("Geen fouten", stats["fouten"] == 0)


def test_fout_in_handler():
    """Test dat een fout in een handler de bus niet crasht."""
    print("\n=== Test 13: Fout Tolerantie ===")
    bus = fresh_bus()
    goede_resultaten = []

    def kapotte_handler(event):
        raise ValueError("Opzettelijke fout!")

    def goede_handler(event):
        goede_resultaten.append(event)

    bus.subscribe("fout_event", kapotte_handler)
    bus.subscribe("fout_event", goede_handler)
    bus.publish("fout_event", {}, bron="test")

    check("Goede handler nog steeds bereikt", len(goede_resultaten) == 1)
    check("Fout geregistreerd", bus.statistieken()["fouten"] >= 1)


def test_thread_safety():
    """Test thread-safe publish vanuit meerdere threads."""
    print("\n=== Test 14: Thread Safety ===")
    bus = fresh_bus()
    ontvangen = []
    lock = threading.Lock()

    def handler(event):
        with lock:
            ontvangen.append(event.data["thread"])

    bus.subscribe("thread_event", handler)

    threads = []
    for i in range(10):
        t = threading.Thread(
            target=bus.publish,
            args=("thread_event", {"thread": i}, f"thread_{i}"),
        )
        threads.append(t)

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    check("Alle thread events ontvangen", len(ontvangen) == 10)
    check("Alle threads vertegenwoordigd",
          set(ontvangen) == set(range(10)))


def test_dubbele_subscribe():
    """Test dat dezelfde callback niet dubbel wordt geregistreerd."""
    print("\n=== Test 15: Dubbele Subscribe ===")
    bus = fresh_bus()
    teller = [0]

    def handler(event):
        teller[0] += 1

    bus.subscribe("dubbel_event", handler)
    bus.subscribe("dubbel_event", handler)  # dubbel
    bus.publish("dubbel_event", {}, bron="test")

    check("Handler maar 1x aangeroepen", teller[0] == 1)


def test_reset():
    """Test bus reset."""
    print("\n=== Test 16: Reset ===")
    bus = fresh_bus()

    bus.subscribe("reset_event", lambda e: None)
    bus.publish("reset_event", {}, bron="test")

    bus.reset()

    stats = bus.statistieken()
    check("Subscribers gewist", stats["subscribers"] == 0)
    check("Stats gereset", stats["events_gepubliceerd"] == 0)
    check("History gewist", stats["events_in_history"] == 0)


def test_event_types_constanten():
    """Test dat EventTypes de verwachte constanten heeft."""
    print("\n=== Test 17: EventTypes Constanten ===")
    from danny_toolkit.core.neural_bus import EventTypes

    check("WEATHER_UPDATE", EventTypes.WEATHER_UPDATE == "weather_update")
    check("HEALTH_STATUS_CHANGE",
          EventTypes.HEALTH_STATUS_CHANGE == "health_status_change")
    check("AGENDA_UPDATE", EventTypes.AGENDA_UPDATE == "agenda_update")
    check("MOOD_UPDATE", EventTypes.MOOD_UPDATE == "mood_update")
    check("SYSTEM_EVENT", EventTypes.SYSTEM_EVENT == "system_event")


def test_cross_app_scenario():
    """Test realistisch cross-app scenario: fitness -> recipe."""
    print("\n=== Test 18: Cross-App Scenario ===")
    bus = fresh_bus()
    recept_context = {}

    def on_health(event):
        recept_context["calorieen"] = event.data.get("calorieen", 0)
        recept_context["doel"] = event.data.get("doel", "fit")

    bus.subscribe("health_status_change", on_health)

    # Fitness tracker publiceert workout
    bus.publish("health_status_change", {
        "type": "kracht",
        "calorieen": 450,
        "duur_min": 60,
        "doel": "opbouwen",
    }, bron="fitness_tracker")

    check("Recipe ontvangt fitness data",
          recept_context.get("calorieen") == 450)
    check("Doel doorgegeven",
          recept_context.get("doel") == "opbouwen")

    # Weer agent publiceert weer
    bus.publish("weather_update", {
        "stad": "Amsterdam",
        "temp": 5,
        "conditie": "regenachtig",
    }, bron="weer_agent")

    ctx = bus.get_context(["health_status_change", "weather_update"])
    check("Cross-app context beschikbaar", len(ctx) == 2)


# ==================== MAIN ====================

if __name__ == "__main__":
    print("=" * 60)
    print("  NEURAL BUS - PUB/SUB TEST SUITE")
    print("=" * 60)

    test_singleton()
    test_publish_subscribe()
    test_meerdere_subscribers()
    test_type_isolatie()
    test_wildcard_subscriber()
    test_unsubscribe()
    test_history()
    test_history_bron_filter()
    test_history_ringbuffer()
    test_get_context()
    test_event_to_dict()
    test_statistieken()
    test_fout_in_handler()
    test_thread_safety()
    test_dubbele_subscribe()
    test_reset()
    test_event_types_constanten()
    test_cross_app_scenario()

    print("\n" + "=" * 60)
    print(f"  RESULTAAT: {geslaagd}/{checks} checks geslaagd"
          f" ({mislukt} mislukt)")
    print("=" * 60)

    sys.exit(0 if mislukt == 0 else 1)
