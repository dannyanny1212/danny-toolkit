"""
Vector Data Studio v1.0 - Visualiseer, Analyseer, Converteer, Deel.
Een geavanceerde app voor vectordata visualisatie en analyse.
"""

import json
import math
import random
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from ..core.config import Config
from ..core.utils import clear_scherm


class VectorStudioApp:
    """Vector Data Studio - Visualiseer, Analyseer, Converteer, Deel."""

    VERSIE = "1.0"

    def __init__(self):
        Config.ensure_dirs()
        self.data_dir = Config.APPS_DATA_DIR / "vector_studio"
        self.data_dir.mkdir(exist_ok=True)
        self.projects_file = self.data_dir / "projects.json"
        self.data = self._laad_data()
        self.huidig_project = None
        self.vectors = []  # Huidige vectoren in geheugen

    def _laad_data(self) -> dict:
        """Laad projecten data."""
        if self.projects_file.exists():
            try:
                with open(self.projects_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {
            "versie": "1.0",
            "projecten": [],
            "statistieken": {
                "totaal_projecten": 0,
                "totaal_vectors": 0,
                "laatste_activiteit": None
            }
        }

    def _sla_op(self):
        """Sla projecten data op."""
        self.data["statistieken"]["laatste_activiteit"] = datetime.now().isoformat()
        with open(self.projects_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def _cosine_similarity(self, vec1: list, vec2: list) -> float:
        """Bereken cosine similarity tussen twee vectoren."""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        dot = sum(a * b for a, b in zip(vec1, vec2))
        mag1 = math.sqrt(sum(a**2 for a in vec1))
        mag2 = math.sqrt(sum(b**2 for b in vec2))
        if mag1 == 0 or mag2 == 0:
            return 0.0
        return dot / (mag1 * mag2)

    def _euclidean_distance(self, vec1: list, vec2: list) -> float:
        """Bereken Euclidische afstand."""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return float("inf")
        return math.sqrt(sum((a - b)**2 for a, b in zip(vec1, vec2)))

    # =========================================================================
    # DIMENSIE REDUCTIE
    # =========================================================================

    def _simple_pca(self, vectors: list, n_components: int = 2) -> list:
        """
        Simpele PCA implementatie zonder externe dependencies.
        Reduceert vectoren naar n_components dimensies.
        """
        if not vectors or len(vectors) < 2:
            return vectors

        # Converteer naar matrix
        n = len(vectors)
        d = len(vectors[0])

        # Centreer data (trek gemiddelde af)
        means = [sum(v[i] for v in vectors) / n for i in range(d)]
        centered = [[v[i] - means[i] for i in range(d)] for v in vectors]

        # Bereken covariantie matrix (versimpeld)
        # We gebruiken power iteration voor de eerste 2 eigenvectoren
        eigenvectors = []

        for _ in range(n_components):
            # Willekeurige startvector
            v = [random.gauss(0, 1) for _ in range(d)]

            # Power iteration (20 iteraties)
            for _ in range(20):
                # Vermenigvuldig met data transpose * data
                new_v = [0.0] * d
                for row in centered:
                    dot = sum(row[j] * v[j] for j in range(d))
                    for j in range(d):
                        new_v[j] += row[j] * dot

                # Normaliseer
                norm = math.sqrt(sum(x**2 for x in new_v))
                if norm > 0:
                    v = [x / norm for x in new_v]

            # Deflateer: verwijder component
            for i, row in enumerate(centered):
                dot = sum(row[j] * v[j] for j in range(d))
                centered[i] = [row[j] - dot * v[j] for j in range(d)]

            eigenvectors.append(v)

        # Projecteer data op eigenvectoren
        result = []
        # Herbereken centered (was gemodificeerd)
        centered = [[vectors[i][j] - means[j] for j in range(d)]
                    for i in range(n)]

        for row in centered:
            projected = [sum(row[j] * ev[j] for j in range(d))
                        for ev in eigenvectors]
            result.append(projected)

        return result

    # =========================================================================
    # HOOFDMENU
    # =========================================================================

    def run(self):
        """Hoofdmenu."""
        while True:
            clear_scherm()
            self._toon_header()

            print("  1. Visualiseren")
            print("  2. Analyseren")
            print("  3. Converteren")
            print("  4. Projecten & Samenwerking")
            print("  5. Instellingen")
            print("  0. Terug")
            print("+" + "=" * 50 + "+")

            keuze = input("\nKeuze: ").strip()

            if keuze == "0":
                break
            elif keuze == "1":
                self._visualize_menu()
            elif keuze == "2":
                self._analyze_menu()
            elif keuze == "3":
                self._converter_menu()
            elif keuze == "4":
                self._projects_menu()
            elif keuze == "5":
                self._instellingen_menu()

    def _toon_header(self):
        """Toon header met project info."""
        print("+" + "=" * 50 + "+")
        print("|        VECTOR DATA STUDIO v1.0                   |")
        print("+" + "=" * 50 + "+")

        # Project info
        if self.huidig_project:
            naam = self.huidig_project["naam"][:20]
            vecs = len(self.vectors)
            print(f"|  Project: {naam:<28} Vectors: {vecs:<4}|")
        else:
            print("|  Geen project geladen                            |")

        # Stats
        stats = self.data["statistieken"]
        print(f"|  Projecten: {stats['totaal_projecten']:<5} "
              f"Totaal vectors: {stats['totaal_vectors']:<10}|")
        print("+" + "-" * 50 + "+")

    # =========================================================================
    # VISUALISATIE MENU
    # =========================================================================

    def _visualize_menu(self):
        """Visualisatie submenu."""
        while True:
            clear_scherm()
            print("+" + "=" * 50 + "+")
            print("|           VISUALISEREN                           |")
            print("+" + "=" * 50 + "+")
            print("|  1. 2D Scatter Plot (PCA)                        |")
            print("|  2. 3D Visualisatie (ASCII)                      |")
            print("|  3. Similarity Heatmap                           |")
            print("|  4. Cluster Map                                  |")
            print("|  5. Word Cloud                                   |")
            print("+" + "-" * 50 + "+")
            print("|  0. Terug                                        |")
            print("+" + "=" * 50 + "+")

            keuze = input("\nKeuze: ").strip()

            if keuze == "0":
                break
            elif keuze == "1":
                self._plot_2d_pca()
            elif keuze == "2":
                self._plot_3d_ascii()
            elif keuze == "3":
                self._show_similarity_heatmap()
            elif keuze == "4":
                self._show_cluster_map()
            elif keuze == "5":
                self._show_word_cloud()

            input("\nDruk op Enter...")

    def _plot_2d_pca(self):
        """2D scatter plot met PCA."""
        print("\n--- 2D SCATTER PLOT (PCA) ---")

        if not self._check_vectors():
            return

        vectors_data = self._get_vectors_from_project()
        if len(vectors_data) < 2:
            print("[!] Minimaal 2 vectoren nodig voor visualisatie.")
            return

        # Extract vectoren en labels
        vecs = [v["embedding"] for v in vectors_data]
        labels = [v.get("tekst", f"v{i}")[:10] for i, v in enumerate(vectors_data)]

        # PCA naar 2D
        print("\n[PCA dimensie reductie...]")
        reduced = self._simple_pca(vecs, n_components=2)

        # Normaliseer naar plot grid
        if not reduced:
            print("[!] PCA mislukt.")
            return

        x_vals = [r[0] for r in reduced]
        y_vals = [r[1] for r in reduced]

        x_min, x_max = min(x_vals), max(x_vals)
        y_min, y_max = min(y_vals), max(y_vals)

        # Vermijd deling door nul
        x_range = x_max - x_min if x_max != x_min else 1
        y_range = y_max - y_min if y_max != y_min else 1

        # Plot grid (40x20)
        width, height = 40, 20
        grid = [[" " for _ in range(width)] for _ in range(height)]

        # Plaats punten
        for i, (x, y) in enumerate(reduced):
            px = int((x - x_min) / x_range * (width - 1))
            py = int((y - y_min) / y_range * (height - 1))
            py = height - 1 - py  # Flip Y

            px = max(0, min(width - 1, px))
            py = max(0, min(height - 1, py))

            # Gebruik eerste letter van label
            marker = labels[i][0].upper() if labels[i] else "."
            grid[py][px] = marker

        # Teken plot
        print("\n  VECTOR SPACE (2D PCA)")
        print("  +" + "-" * width + "+")
        for row in grid:
            print("  |" + "".join(row) + "|")
        print("  +" + "-" * width + "+")

        # Legenda
        print("\n  Legenda:")
        for i, label in enumerate(labels[:10]):  # Max 10
            print(f"    {labels[i][0].upper()} = {label}")
        if len(labels) > 10:
            print(f"    ... en {len(labels) - 10} meer")

    def _plot_3d_ascii(self):
        """3D ASCII visualisatie."""
        print("\n--- 3D VISUALISATIE (ASCII) ---")

        if not self._check_vectors():
            return

        vectors_data = self._get_vectors_from_project()
        if len(vectors_data) < 2:
            print("[!] Minimaal 2 vectoren nodig.")
            return

        vecs = [v["embedding"] for v in vectors_data]
        labels = [v.get("tekst", f"v{i}")[:8] for i, v in enumerate(vectors_data)]

        # PCA naar 3D
        reduced = self._simple_pca(vecs, n_components=3)
        if not reduced or len(reduced[0]) < 3:
            print("[!] Kon niet naar 3D reduceren.")
            return

        # Simpele isometrische projectie
        print("\n  3D VECTOR SPACE (Isometrisch)")
        print("  " + "=" * 44)

        # Normaliseer
        x_vals = [r[0] for r in reduced]
        y_vals = [r[1] for r in reduced]
        z_vals = [r[2] for r in reduced]

        def normalize(vals):
            mn, mx = min(vals), max(vals)
            rng = mx - mn if mx != mn else 1
            return [(v - mn) / rng for v in vals]

        x_norm = normalize(x_vals)
        y_norm = normalize(y_vals)
        z_norm = normalize(z_vals)

        # Sorteer op Z (achter naar voor)
        sorted_idx = sorted(range(len(reduced)), key=lambda i: z_norm[i])

        # Plot met diepte
        for i in sorted_idx:
            x, y, z = x_norm[i], y_norm[i], z_norm[i]
            # Isometrische projectie
            screen_x = int((x - y) * 20 + 22)
            screen_y = int((x + y) / 2 * 10 - z * 5 + 5)
            screen_y = max(0, min(9, screen_y))

            # Diepte indicator
            depth_char = [".", "o", "O", "@"][min(3, int(z * 4))]
            indent = " " * max(0, screen_x)
            label = labels[i][:6]
            print(f"  {indent}{depth_char}{label}")

        print("  " + "=" * 44)
        print("  Diepte: . = ver  @ = dichtbij")

    def _show_similarity_heatmap(self):
        """Toon similarity matrix als heatmap."""
        print("\n--- SIMILARITY HEATMAP ---")

        if not self._check_vectors():
            return

        vectors_data = self._get_vectors_from_project()
        if len(vectors_data) < 2:
            print("[!] Minimaal 2 vectoren nodig.")
            return

        # Max 10 voor leesbaarheid
        if len(vectors_data) > 10:
            print(f"[!] Te veel vectoren ({len(vectors_data)}), "
                  "toon eerste 10.")
            vectors_data = vectors_data[:10]

        n = len(vectors_data)
        vecs = [v["embedding"] for v in vectors_data]
        labels = [v.get("tekst", f"v{i}")[:6] for i, v in enumerate(vectors_data)]

        # Bereken similarity matrix
        matrix = []
        for i in range(n):
            row = []
            for j in range(n):
                sim = self._cosine_similarity(vecs[i], vecs[j])
                row.append(sim)
            matrix.append(row)

        # Teken heatmap
        print("\n  SIMILARITY MATRIX")
        print("  " + " " * 7 + "  ".join(f"{l:>6}" for l in labels))

        heat_chars = ["░", "▒", "▓", "█"]

        for i, row in enumerate(matrix):
            line = f"  {labels[i]:>6} "
            for sim in row:
                # Kies karakter op basis van similarity
                idx = min(3, int(sim * 4))
                char = heat_chars[idx]
                line += f"[{sim:.2f}]"
            print(line)

        # Legenda
        print(f"\n  Legenda: [1.0]={heat_chars[3]*4} "
              f"[0.5]={heat_chars[2]*4} [0.0]={heat_chars[0]*4}")

    def _show_cluster_map(self):
        """Toon cluster visualisatie."""
        print("\n--- CLUSTER MAP ---")

        if not self._check_vectors():
            return

        vectors_data = self._get_vectors_from_project()
        if len(vectors_data) < 3:
            print("[!] Minimaal 3 vectoren nodig voor clustering.")
            return

        vecs = [v["embedding"] for v in vectors_data]
        labels = [v.get("tekst", f"v{i}")[:12] for i, v in enumerate(vectors_data)]

        # Simpele K-means (k=3)
        k = min(3, len(vectors_data) // 2)
        clusters = self._simple_kmeans(vecs, k)

        # Groepeer per cluster
        print(f"\n  {k} CLUSTERS GEVONDEN")
        print("  " + "=" * 44)

        for cluster_id in range(k):
            members = [i for i, c in enumerate(clusters) if c == cluster_id]
            print(f"\n  Cluster {cluster_id + 1} ({len(members)} vectors):")

            # Bereken centroid similarity
            if members:
                for idx in members[:5]:  # Max 5 per cluster
                    print(f"    * {labels[idx]}")
                if len(members) > 5:
                    print(f"    ... en {len(members) - 5} meer")

        print("\n  " + "=" * 44)

    def _simple_kmeans(self, vectors: list, k: int, max_iter: int = 10) -> list:
        """Simpele K-means clustering."""
        if not vectors or k < 1:
            return []

        n = len(vectors)
        d = len(vectors[0])

        # Willekeurige startcentroids
        indices = random.sample(range(n), min(k, n))
        centroids = [vectors[i][:] for i in indices]

        clusters = [0] * n

        for _ in range(max_iter):
            # Wijs toe aan dichtstbijzijnde centroid
            for i, v in enumerate(vectors):
                min_dist = float("inf")
                for c_idx, centroid in enumerate(centroids):
                    dist = self._euclidean_distance(v, centroid)
                    if dist < min_dist:
                        min_dist = dist
                        clusters[i] = c_idx

            # Update centroids
            for c_idx in range(k):
                members = [vectors[i] for i in range(n) if clusters[i] == c_idx]
                if members:
                    centroids[c_idx] = [
                        sum(m[j] for m in members) / len(members)
                        for j in range(d)
                    ]

        return clusters

    def _show_word_cloud(self):
        """Toon word cloud van teksten."""
        print("\n--- WORD CLOUD ---")

        if not self._check_vectors():
            return

        vectors_data = self._get_vectors_from_project()

        # Verzamel alle woorden
        woorden = {}
        for v in vectors_data:
            tekst = v.get("tekst", "")
            for woord in tekst.lower().split():
                woord = "".join(c for c in woord if c.isalnum())
                if len(woord) > 2:
                    woorden[woord] = woorden.get(woord, 0) + 1

        if not woorden:
            print("[!] Geen teksten gevonden in vectoren.")
            return

        # Sorteer op frequentie
        gesorteerd = sorted(woorden.items(), key=lambda x: -x[1])[:30]

        # Teken word cloud
        print("\n  WORD CLOUD")
        print("  " + "=" * 44)

        max_freq = gesorteerd[0][1] if gesorteerd else 1
        lijn = "  "

        for woord, freq in gesorteerd:
            # Schaal grootte
            size = int((freq / max_freq) * 3) + 1
            formatted = woord.upper() if size >= 3 else woord
            if size >= 2:
                formatted = f"[{formatted}]"

            if len(lijn) + len(formatted) + 1 > 50:
                print(lijn)
                lijn = "  "

            lijn += formatted + " "

        if lijn.strip():
            print(lijn)

        print("\n  " + "=" * 44)
        print(f"  Top 5: {', '.join(w for w, _ in gesorteerd[:5])}")

    # =========================================================================
    # ANALYSE MENU
    # =========================================================================

    def _analyze_menu(self):
        """Analyse submenu."""
        while True:
            clear_scherm()
            print("+" + "=" * 50 + "+")
            print("|              ANALYSEREN                          |")
            print("+" + "=" * 50 + "+")
            print("|  1. Statistieken Dashboard                       |")
            print("|  2. Vind Vergelijkbare Vectoren                  |")
            print("|  3. Outlier Detectie                             |")
            print("|  4. Cluster Analyse                              |")
            print("|  5. Kwaliteits Beoordeling                       |")
            print("+" + "-" * 50 + "+")
            print("|  0. Terug                                        |")
            print("+" + "=" * 50 + "+")

            keuze = input("\nKeuze: ").strip()

            if keuze == "0":
                break
            elif keuze == "1":
                self._show_statistics()
            elif keuze == "2":
                self._find_similar()
            elif keuze == "3":
                self._detect_outliers()
            elif keuze == "4":
                self._cluster_analysis()
            elif keuze == "5":
                self._quality_assessment()

            input("\nDruk op Enter...")

    def _show_statistics(self):
        """Toon statistieken dashboard."""
        print("\n" + "=" * 48)
        print("          VECTOR STUDIO DASHBOARD")
        print("=" * 48)

        if not self._check_vectors(silent=True):
            print("|  Geen vectoren geladen.                         |")
            print("|  Laad eerst een project of importeer data.      |")
            print("=" * 48)
            return

        vectors_data = self._get_vectors_from_project()
        n = len(vectors_data)

        if n == 0:
            print("|  Project bevat geen vectoren.                   |")
            print("=" * 48)
            return

        # Basis stats
        dims = len(vectors_data[0]["embedding"]) if vectors_data else 0

        # Bereken gemiddelde similarity
        avg_sim = 0.0
        count = 0
        sample_size = min(50, n)  # Sample voor snelheid
        sample = random.sample(vectors_data, sample_size) if n > 50 else vectors_data

        for i, v1 in enumerate(sample):
            for v2 in sample[i+1:]:
                avg_sim += self._cosine_similarity(v1["embedding"], v2["embedding"])
                count += 1

        avg_sim = avg_sim / count if count > 0 else 0

        # Outliers (simpele detectie)
        outliers = self._count_outliers(vectors_data)

        # Clusters (schat)
        estimated_clusters = self._estimate_clusters(vectors_data)

        # Quality score
        quality = self._calculate_quality(vectors_data)

        print(f"|  Vectors:     {n:<7} | Dimensies: {dims:<8}|")
        print(f"|  Clusters:    {estimated_clusters:<7} | Outliers:  {outliers:<8}|")
        print(f"|  Avg Sim:     {avg_sim:.2f}    | Quality:   {quality}%       |")
        print("=" * 48)

        # Top clusters (als we er hebben)
        if n >= 3:
            vecs = [v["embedding"] for v in vectors_data]
            k = min(3, n // 2)
            clusters = self._simple_kmeans(vecs, k)

            print("|  Top Clusters:                                  |")
            for c in range(k):
                count = clusters.count(c)
                print(f"|    {c+1}. Cluster {c+1} ({count} vectors)                    |")

        print("=" * 48)

    def _count_outliers(self, vectors_data: list) -> int:
        """Tel aantal outliers."""
        if len(vectors_data) < 5:
            return 0

        vecs = [v["embedding"] for v in vectors_data]
        outliers = 0

        for i, v1 in enumerate(vecs):
            # Bereken gemiddelde similarity met anderen
            sims = [self._cosine_similarity(v1, v2)
                    for j, v2 in enumerate(vecs) if i != j]
            avg_sim = sum(sims) / len(sims) if sims else 0

            # Outlier als gemiddelde similarity < 0.3
            if avg_sim < 0.3:
                outliers += 1

        return outliers

    def _estimate_clusters(self, vectors_data: list) -> int:
        """Schat optimaal aantal clusters."""
        n = len(vectors_data)
        if n < 3:
            return 1
        # Vuistregel: sqrt(n/2)
        return max(1, int(math.sqrt(n / 2)))

    def _calculate_quality(self, vectors_data: list) -> int:
        """Bereken kwaliteitsscore (0-100)."""
        if not vectors_data:
            return 0

        score = 100

        # Check dimensies consistentie
        dims = [len(v["embedding"]) for v in vectors_data]
        if len(set(dims)) > 1:
            score -= 30  # Inconsistente dimensies

        # Check voor lege of near-zero vectoren
        zero_count = 0
        for v in vectors_data:
            mag = math.sqrt(sum(x**2 for x in v["embedding"]))
            if mag < 0.01:
                zero_count += 1

        if zero_count > 0:
            score -= min(30, zero_count * 5)

        # Check voor te veel outliers
        outliers = self._count_outliers(vectors_data)
        outlier_ratio = outliers / len(vectors_data)
        if outlier_ratio > 0.3:
            score -= 20
        elif outlier_ratio > 0.1:
            score -= 10

        return max(0, score)

    def _find_similar(self):
        """Vind vergelijkbare vectoren."""
        print("\n--- VIND VERGELIJKBARE VECTOREN ---")

        if not self._check_vectors():
            return

        vectors_data = self._get_vectors_from_project()

        # Toon beschikbare vectoren
        print("\nBeschikbare vectoren:")
        for i, v in enumerate(vectors_data[:10]):
            tekst = v.get("tekst", f"Vector {i}")[:30]
            print(f"  {i + 1}. {tekst}")
        if len(vectors_data) > 10:
            print(f"  ... en {len(vectors_data) - 10} meer")

        try:
            idx = int(input("\nKies vector nummer: ").strip()) - 1
            if idx < 0 or idx >= len(vectors_data):
                print("[!] Ongeldige keuze.")
                return
        except ValueError:
            print("[!] Voer een nummer in.")
            return

        # Vind meest vergelijkbare
        target = vectors_data[idx]
        similarities = []

        for i, v in enumerate(vectors_data):
            if i != idx:
                sim = self._cosine_similarity(target["embedding"], v["embedding"])
                similarities.append((i, v, sim))

        similarities.sort(key=lambda x: -x[2])

        print(f"\nMeest vergelijkbaar met '{target.get('tekst', 'Vector')[:20]}':")
        print("-" * 44)

        for i, v, sim in similarities[:5]:
            tekst = v.get("tekst", f"Vector {i}")[:25]
            bar = "█" * int(sim * 10)
            print(f"  {sim:.3f} {bar:<10} {tekst}")

    def _detect_outliers(self):
        """Detecteer outliers."""
        print("\n--- OUTLIER DETECTIE ---")

        if not self._check_vectors():
            return

        vectors_data = self._get_vectors_from_project()
        if len(vectors_data) < 5:
            print("[!] Minimaal 5 vectoren nodig.")
            return

        vecs = [v["embedding"] for v in vectors_data]
        outliers = []

        print("\n[Analyseren...]")

        for i, v1 in enumerate(vecs):
            sims = [self._cosine_similarity(v1, v2)
                    for j, v2 in enumerate(vecs) if i != j]
            avg_sim = sum(sims) / len(sims)

            if avg_sim < 0.3:
                outliers.append((i, vectors_data[i], avg_sim))

        if not outliers:
            print("\n[OK] Geen outliers gedetecteerd!")
            return

        outliers.sort(key=lambda x: x[2])

        print(f"\n{len(outliers)} OUTLIERS GEVONDEN:")
        print("-" * 44)

        for i, v, avg_sim in outliers:
            tekst = v.get("tekst", f"Vector {i}")[:25]
            print(f"  [{avg_sim:.2f}] {tekst}")
            print(f"         ID: {i}, Gemiddelde similarity: {avg_sim:.3f}")

    def _cluster_analysis(self):
        """Gedetailleerde cluster analyse."""
        print("\n--- CLUSTER ANALYSE ---")

        if not self._check_vectors():
            return

        vectors_data = self._get_vectors_from_project()
        if len(vectors_data) < 4:
            print("[!] Minimaal 4 vectoren nodig.")
            return

        # Vraag aantal clusters
        suggested_k = self._estimate_clusters(vectors_data)
        k_input = input(f"Aantal clusters (suggestie: {suggested_k}): ").strip()

        try:
            k = int(k_input) if k_input else suggested_k
            k = max(2, min(k, len(vectors_data) // 2))
        except ValueError:
            k = suggested_k

        vecs = [v["embedding"] for v in vectors_data]
        clusters = self._simple_kmeans(vecs, k, max_iter=20)

        print(f"\n{k} CLUSTERS ANALYSE")
        print("=" * 48)

        for cluster_id in range(k):
            members = [(i, vectors_data[i])
                       for i in range(len(vectors_data)) if clusters[i] == cluster_id]

            print(f"\nCluster {cluster_id + 1}: {len(members)} vectoren")
            print("-" * 40)

            # Bereken intra-cluster similarity
            if len(members) > 1:
                cluster_vecs = [m[1]["embedding"] for m in members]
                sims = []
                for i, v1 in enumerate(cluster_vecs):
                    for v2 in cluster_vecs[i+1:]:
                        sims.append(self._cosine_similarity(v1, v2))
                avg_sim = sum(sims) / len(sims) if sims else 0
                print(f"  Cohesie: {avg_sim:.3f}")

            # Toon leden
            for idx, v in members[:5]:
                tekst = v.get("tekst", f"Vector {idx}")[:30]
                print(f"    * {tekst}")
            if len(members) > 5:
                print(f"    ... en {len(members) - 5} meer")

        print("\n" + "=" * 48)

    def _quality_assessment(self):
        """Beoordeel kwaliteit van embeddings."""
        print("\n--- KWALITEITS BEOORDELING ---")

        if not self._check_vectors():
            return

        vectors_data = self._get_vectors_from_project()

        print("\n[Analyseren...]")

        # Check 1: Dimensie consistentie
        dims = [len(v["embedding"]) for v in vectors_data]
        unique_dims = set(dims)
        dim_ok = len(unique_dims) == 1

        # Check 2: Zero/near-zero vectoren
        zero_vectors = []
        for i, v in enumerate(vectors_data):
            mag = math.sqrt(sum(x**2 for x in v["embedding"]))
            if mag < 0.01:
                zero_vectors.append(i)

        # Check 3: Duplicaten (zeer hoge similarity)
        duplicates = []
        for i in range(min(100, len(vectors_data))):
            for j in range(i + 1, min(100, len(vectors_data))):
                sim = self._cosine_similarity(
                    vectors_data[i]["embedding"],
                    vectors_data[j]["embedding"]
                )
                if sim > 0.99:
                    duplicates.append((i, j))

        # Check 4: Outliers
        outliers = self._count_outliers(vectors_data)

        # Bereken score
        score = 100
        issues = []

        if not dim_ok:
            score -= 30
            issues.append(f"Inconsistente dimensies: {unique_dims}")

        if zero_vectors:
            score -= min(20, len(zero_vectors) * 5)
            issues.append(f"{len(zero_vectors)} zero/near-zero vectoren")

        if duplicates:
            score -= min(20, len(duplicates) * 2)
            issues.append(f"{len(duplicates)} mogelijke duplicaten")

        if outliers > len(vectors_data) * 0.2:
            score -= 15
            issues.append(f"{outliers} outliers (>20%)")

        score = max(0, score)

        # Rapport
        print("\n" + "=" * 48)
        print("          KWALITEITS RAPPORT")
        print("=" * 48)
        print(f"|  Score: {score}/100 {''.join(['*' for _ in range(score // 10)])}{''.join(['-' for _ in range(10 - score // 10)])} |")
        print("=" * 48)

        if score >= 80:
            print("|  Status: GOED                                  |")
        elif score >= 60:
            print("|  Status: ACCEPTABEL                            |")
        elif score >= 40:
            print("|  Status: VERBETERING NODIG                     |")
        else:
            print("|  Status: KRITIEK                               |")

        print("=" * 48)

        if issues:
            print("\nGevonden problemen:")
            for issue in issues:
                print(f"  [!] {issue}")
        else:
            print("\n[OK] Geen problemen gevonden!")

        print("\nDetails:")
        print(f"  Vectoren: {len(vectors_data)}")
        print(f"  Dimensies: {dims[0] if dims else 0}")
        print(f"  Zero vectoren: {len(zero_vectors)}")
        print(f"  Duplicaten: {len(duplicates)}")
        print(f"  Outliers: {outliers}")

    # =========================================================================
    # CONVERTER MENU
    # =========================================================================

    def _converter_menu(self):
        """Converter submenu."""
        while True:
            clear_scherm()
            print("+" + "=" * 50 + "+")
            print("|             CONVERTEREN                          |")
            print("+" + "=" * 50 + "+")
            print("|  1. Import Data                                  |")
            print("|  2. Export Data                                  |")
            print("|  3. Tekst naar Vector                            |")
            print("|  4. Batch Conversie                              |")
            print("+" + "-" * 50 + "+")
            print("|  0. Terug                                        |")
            print("+" + "=" * 50 + "+")

            keuze = input("\nKeuze: ").strip()

            if keuze == "0":
                break
            elif keuze == "1":
                self._import_data()
            elif keuze == "2":
                self._export_data()
            elif keuze == "3":
                self._text_to_vector()
            elif keuze == "4":
                self._batch_convert()

            input("\nDruk op Enter...")

    def _import_data(self):
        """Import data wizard."""
        print("\n--- IMPORT DATA ---")
        print("\nFormaten:")
        print("  1. JSON bestand")
        print("  2. CSV bestand")
        print("  3. TXT bestand (teksten)")
        print("  4. Bestaande VectorStore")

        keuze = input("\nKeuze: ").strip()

        if keuze == "1":
            self._import_json()
        elif keuze == "2":
            self._import_csv()
        elif keuze == "3":
            self._import_txt()
        elif keuze == "4":
            self._import_vectorstore()

    def _import_json(self):
        """Import vanuit JSON bestand."""
        print("\n[JSON Import]")
        pad = input("Pad naar JSON bestand: ").strip()

        if not pad:
            return

        try:
            path = Path(pad)
            if not path.exists():
                print(f"[!] Bestand niet gevonden: {pad}")
                return

            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Probeer vectoren te extraheren
            vectors = []
            if isinstance(data, list):
                vectors = data
            elif isinstance(data, dict):
                if "documenten" in data:
                    vectors = list(data["documenten"].values())
                elif "vectors" in data:
                    vectors = data["vectors"]

            if not vectors:
                print("[!] Geen vectoren gevonden in bestand.")
                return

            # Maak project
            naam = input("Project naam: ").strip() or path.stem
            self._create_project_with_vectors(naam, vectors)

            print(f"[OK] {len(vectors)} vectoren geimporteerd naar '{naam}'!")

        except (json.JSONDecodeError, IOError) as e:
            print(f"[!] Import fout: {e}")

    def _import_csv(self):
        """Import vanuit CSV bestand."""
        print("\n[CSV Import]")
        pad = input("Pad naar CSV bestand: ").strip()

        if not pad:
            return

        try:
            path = Path(pad)
            if not path.exists():
                print(f"[!] Bestand niet gevonden: {pad}")
                return

            vectors = []
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Skip header
            for line in lines[1:]:
                parts = line.strip().split(",")
                if len(parts) >= 2:
                    tekst = parts[0]
                    # Probeer embedding te parsen
                    try:
                        embedding = [float(x) for x in parts[1:] if x.strip()]
                        if embedding:
                            vectors.append({
                                "tekst": tekst,
                                "embedding": embedding
                            })
                    except ValueError:
                        # Geen embedding, maak dummy
                        vectors.append({
                            "tekst": tekst,
                            "embedding": self._dummy_embedding(tekst)
                        })

            if not vectors:
                print("[!] Geen data gevonden.")
                return

            naam = input("Project naam: ").strip() or path.stem
            self._create_project_with_vectors(naam, vectors)

            print(f"[OK] {len(vectors)} items geimporteerd!")

        except IOError as e:
            print(f"[!] Import fout: {e}")

    def _import_txt(self):
        """Import teksten uit TXT bestand."""
        print("\n[TXT Import]")
        pad = input("Pad naar TXT bestand: ").strip()

        if not pad:
            return

        try:
            path = Path(pad)
            if not path.exists():
                print(f"[!] Bestand niet gevonden: {pad}")
                return

            with open(path, "r", encoding="utf-8") as f:
                inhoud = f.read()

            # Split op lege regels of newlines
            paragrafen = [p.strip() for p in inhoud.split("\n\n") if p.strip()]
            if not paragrafen:
                paragrafen = [p.strip() for p in inhoud.split("\n") if p.strip()]

            vectors = []
            for tekst in paragrafen:
                if len(tekst) > 10:  # Filter korte fragmenten
                    vectors.append({
                        "tekst": tekst,
                        "embedding": self._dummy_embedding(tekst)
                    })

            if not vectors:
                print("[!] Geen teksten gevonden.")
                return

            naam = input("Project naam: ").strip() or path.stem
            self._create_project_with_vectors(naam, vectors)

            print(f"[OK] {len(vectors)} teksten geimporteerd!")
            print("[!] Dummy embeddings gebruikt. Gebruik 'Tekst naar Vector'")
            print("    om echte embeddings te genereren.")

        except IOError as e:
            print(f"[!] Import fout: {e}")

    def _import_vectorstore(self):
        """Import vanuit bestaande VectorStore."""
        print("\n[VectorStore Import]")

        # Zoek bestaande stores
        rag_dir = Config.RAG_DATA_DIR
        stores = list(rag_dir.glob("vector_db*.json"))

        if not stores:
            print("[!] Geen VectorStores gevonden.")
            return

        print("\nBeschikbare VectorStores:")
        for i, store in enumerate(stores):
            print(f"  {i + 1}. {store.name}")

        try:
            idx = int(input("\nKeuze: ").strip()) - 1
            if idx < 0 or idx >= len(stores):
                return

            with open(stores[idx], "r", encoding="utf-8") as f:
                data = json.load(f)

            docs = data.get("documenten", {})
            vectors = []

            for doc_id, doc_data in docs.items():
                vectors.append({
                    "id": doc_id,
                    "tekst": doc_data.get("tekst", ""),
                    "embedding": doc_data.get("embedding", []),
                    "metadata": doc_data.get("metadata", {})
                })

            if not vectors:
                print("[!] Geen vectoren in store.")
                return

            naam = input("Project naam: ").strip() or stores[idx].stem
            self._create_project_with_vectors(naam, vectors)

            print(f"[OK] {len(vectors)} vectoren geimporteerd!")

        except (ValueError, json.JSONDecodeError, IOError) as e:
            print(f"[!] Import fout: {e}")

    def _dummy_embedding(self, tekst: str, dims: int = 256) -> list:
        """Genereer dummy embedding op basis van tekst hash."""
        import hashlib
        vector = [0.0] * dims

        woorden = tekst.lower().split()
        for woord in woorden:
            woord = "".join(c for c in woord if c.isalnum())
            if len(woord) > 2:
                h = int(hashlib.sha256(woord.encode()).hexdigest(), 16)
                vector[h % dims] += 1.0

        # Normaliseer
        norm = math.sqrt(sum(v**2 for v in vector))
        if norm > 0:
            vector = [v / norm for v in vector]

        return vector

    def _export_data(self):
        """Export data wizard."""
        print("\n--- EXPORT DATA ---")

        if not self._check_vectors():
            return

        print("\nFormaten:")
        print("  1. JSON")
        print("  2. CSV")
        print("  3. Markdown Rapport")

        keuze = input("\nKeuze: ").strip()

        vectors_data = self._get_vectors_from_project()
        project_naam = self.huidig_project["naam"] if self.huidig_project else "export"

        if keuze == "1":
            self._export_json(vectors_data, project_naam)
        elif keuze == "2":
            self._export_csv(vectors_data, project_naam)
        elif keuze == "3":
            self._export_markdown(vectors_data, project_naam)

    def _export_json(self, vectors: list, naam: str):
        """Export naar JSON."""
        output_path = Config.OUTPUT_DIR / f"{naam}_vectors.json"

        data = {
            "naam": naam,
            "export_datum": datetime.now().isoformat(),
            "aantal_vectors": len(vectors),
            "vectors": vectors
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"[OK] Geexporteerd naar: {output_path}")

    def _export_csv(self, vectors: list, naam: str):
        """Export naar CSV."""
        output_path = Config.OUTPUT_DIR / f"{naam}_vectors.csv"

        with open(output_path, "w", encoding="utf-8") as f:
            # Header
            if vectors and "embedding" in vectors[0]:
                dims = len(vectors[0]["embedding"])
                header = "tekst," + ",".join(f"dim_{i}" for i in range(dims))
                f.write(header + "\n")

                for v in vectors:
                    tekst = v.get("tekst", "").replace(",", ";")
                    emb = ",".join(str(x) for x in v["embedding"])
                    f.write(f"{tekst},{emb}\n")

        print(f"[OK] Geexporteerd naar: {output_path}")

    def _export_markdown(self, vectors: list, naam: str):
        """Export naar Markdown rapport."""
        output_path = Config.OUTPUT_DIR / f"{naam}_rapport.md"

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"# Vector Data Rapport: {naam}\n\n")
            f.write(f"*Gegenereerd op: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n")

            f.write("## Overzicht\n\n")
            f.write(f"- **Aantal vectoren:** {len(vectors)}\n")
            if vectors:
                dims = len(vectors[0].get("embedding", []))
                f.write(f"- **Dimensies:** {dims}\n")

            f.write("\n## Vectoren\n\n")
            for i, v in enumerate(vectors[:50]):  # Max 50
                tekst = v.get("tekst", f"Vector {i}")[:50]
                f.write(f"{i + 1}. {tekst}\n")

            if len(vectors) > 50:
                f.write(f"\n*... en {len(vectors) - 50} meer vectoren*\n")

        print(f"[OK] Rapport geexporteerd naar: {output_path}")

    def _text_to_vector(self):
        """Converteer tekst naar vector."""
        print("\n--- TEKST NAAR VECTOR ---")

        tekst = input("Voer tekst in: ").strip()
        if not tekst:
            return

        # Genereer embedding
        embedding = self._dummy_embedding(tekst)

        print(f"\n[OK] Vector gegenereerd!")
        print(f"  Tekst: {tekst[:50]}...")
        print(f"  Dimensies: {len(embedding)}")
        print(f"  Eerste 5 waarden: {embedding[:5]}")

        # Optie om toe te voegen
        if self.huidig_project:
            toevoegen = input("\nToevoegen aan huidig project? (j/n): ").strip().lower()
            if toevoegen == "j":
                self.vectors.append({
                    "tekst": tekst,
                    "embedding": embedding,
                    "toegevoegd_op": datetime.now().isoformat()
                })
                self._save_current_project()
                print("[OK] Toegevoegd!")

    def _batch_convert(self):
        """Batch conversie van teksten."""
        print("\n--- BATCH CONVERSIE ---")

        print("\nVoer teksten in (lege regel om te stoppen):")
        teksten = []

        while True:
            tekst = input(f"{len(teksten) + 1}> ").strip()
            if not tekst:
                break
            teksten.append(tekst)

        if not teksten:
            return

        print(f"\n[Converteer {len(teksten)} teksten...]")

        vectors = []
        for tekst in teksten:
            embedding = self._dummy_embedding(tekst)
            vectors.append({
                "tekst": tekst,
                "embedding": embedding,
                "toegevoegd_op": datetime.now().isoformat()
            })

        print(f"[OK] {len(vectors)} vectoren gegenereerd!")

        # Optie om project te maken
        maak_project = input("\nNieuw project maken met deze vectoren? (j/n): ").strip().lower()
        if maak_project == "j":
            naam = input("Project naam: ").strip() or "Batch Import"
            self._create_project_with_vectors(naam, vectors)
            print(f"[OK] Project '{naam}' aangemaakt!")

    # =========================================================================
    # PROJECTEN MENU
    # =========================================================================

    def _projects_menu(self):
        """Projecten en samenwerking submenu."""
        while True:
            clear_scherm()
            print("+" + "=" * 50 + "+")
            print("|       PROJECTEN & SAMENWERKING                   |")
            print("+" + "=" * 50 + "+")
            print("|  1. Nieuw Project                                |")
            print("|  2. Project Laden                                |")
            print("|  3. Projecten Bekijken                           |")
            print("|  4. Commentaar Toevoegen                         |")
            print("|  5. Versie Historie                              |")
            print("|  6. Project Verwijderen                          |")
            print("+" + "-" * 50 + "+")
            print("|  0. Terug                                        |")
            print("+" + "=" * 50 + "+")

            if self.huidig_project:
                print(f"\n  Huidig project: {self.huidig_project['naam']}")

            keuze = input("\nKeuze: ").strip()

            if keuze == "0":
                break
            elif keuze == "1":
                self._create_project()
            elif keuze == "2":
                self._load_project()
            elif keuze == "3":
                self._view_projects()
            elif keuze == "4":
                self._add_comment()
            elif keuze == "5":
                self._view_history()
            elif keuze == "6":
                self._delete_project()

            input("\nDruk op Enter...")

    def _create_project(self):
        """Maak nieuw project."""
        print("\n--- NIEUW PROJECT ---")

        naam = input("Project naam: ").strip()
        if not naam:
            print("[!] Naam is verplicht.")
            return

        beschrijving = input("Beschrijving (optioneel): ").strip()

        project_id = f"proj_{len(self.data['projecten']) + 1:03d}"
        project = {
            "id": project_id,
            "naam": naam,
            "beschrijving": beschrijving,
            "aangemaakt": datetime.now().isoformat(),
            "vector_file": f"{project_id}_vectors.json",
            "versies": [
                {
                    "id": "v1",
                    "datum": datetime.now().isoformat(),
                    "vectors_count": 0,
                    "beschrijving": "Initiele versie"
                }
            ],
            "commentaren": []
        }

        self.data["projecten"].append(project)
        self.data["statistieken"]["totaal_projecten"] = len(self.data["projecten"])
        self._sla_op()

        # Maak lege vector file
        vector_file = self.data_dir / project["vector_file"]
        with open(vector_file, "w", encoding="utf-8") as f:
            json.dump({"vectors": []}, f)

        self.huidig_project = project
        self.vectors = []

        print(f"\n[OK] Project '{naam}' aangemaakt!")
        print(f"     ID: {project_id}")

    def _create_project_with_vectors(self, naam: str, vectors: list):
        """Maak project met bestaande vectoren."""
        project_id = f"proj_{len(self.data['projecten']) + 1:03d}"

        project = {
            "id": project_id,
            "naam": naam,
            "beschrijving": f"Geimporteerd op {datetime.now().strftime('%Y-%m-%d')}",
            "aangemaakt": datetime.now().isoformat(),
            "vector_file": f"{project_id}_vectors.json",
            "versies": [
                {
                    "id": "v1",
                    "datum": datetime.now().isoformat(),
                    "vectors_count": len(vectors),
                    "beschrijving": "Import"
                }
            ],
            "commentaren": []
        }

        self.data["projecten"].append(project)
        self.data["statistieken"]["totaal_projecten"] = len(self.data["projecten"])
        self.data["statistieken"]["totaal_vectors"] += len(vectors)
        self._sla_op()

        # Sla vectoren op
        vector_file = self.data_dir / project["vector_file"]
        with open(vector_file, "w", encoding="utf-8") as f:
            json.dump({"vectors": vectors}, f, indent=2, ensure_ascii=False)

        self.huidig_project = project
        self.vectors = vectors

    def _load_project(self):
        """Laad een project."""
        print("\n--- PROJECT LADEN ---")

        if not self.data["projecten"]:
            print("[!] Geen projecten gevonden.")
            return

        print("\nBeschikbare projecten:")
        for i, p in enumerate(self.data["projecten"]):
            print(f"  {i + 1}. {p['naam']} ({p['id']})")

        try:
            idx = int(input("\nKeuze: ").strip()) - 1
            if idx < 0 or idx >= len(self.data["projecten"]):
                print("[!] Ongeldige keuze.")
                return

            project = self.data["projecten"][idx]

            # Laad vectoren
            vector_file = self.data_dir / project["vector_file"]
            if vector_file.exists():
                with open(vector_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.vectors = data.get("vectors", [])
            else:
                self.vectors = []

            self.huidig_project = project

            print(f"\n[OK] Project '{project['naam']}' geladen!")
            print(f"     {len(self.vectors)} vectoren in geheugen.")

        except (ValueError, IOError) as e:
            print(f"[!] Laden mislukt: {e}")

    def _view_projects(self):
        """Bekijk alle projecten."""
        print("\n--- ALLE PROJECTEN ---")

        if not self.data["projecten"]:
            print("Geen projecten gevonden.")
            return

        for p in self.data["projecten"]:
            actief = " [ACTIEF]" if self.huidig_project and \
                     self.huidig_project["id"] == p["id"] else ""
            print(f"\n  {p['naam']}{actief}")
            print(f"  ID: {p['id']}")
            print(f"  Aangemaakt: {p['aangemaakt'][:10]}")
            print(f"  Versies: {len(p['versies'])}")
            print(f"  Commentaren: {len(p['commentaren'])}")
            if p.get("beschrijving"):
                print(f"  {p['beschrijving'][:50]}")

    def _add_comment(self):
        """Voeg commentaar toe aan vector of project."""
        print("\n--- COMMENTAAR TOEVOEGEN ---")

        if not self.huidig_project:
            print("[!] Laad eerst een project.")
            return

        print("\nCommentaar op:")
        print("  1. Project algemeen")
        print("  2. Specifieke vector")

        keuze = input("\nKeuze: ").strip()

        if keuze == "1":
            commentaar = input("Commentaar: ").strip()
            if commentaar:
                self.huidig_project["commentaren"].append({
                    "id": f"c{len(self.huidig_project['commentaren']) + 1}",
                    "type": "project",
                    "tekst": commentaar,
                    "datum": datetime.now().isoformat()
                })
                self._sla_op()
                print("[OK] Commentaar toegevoegd!")

        elif keuze == "2":
            if not self.vectors:
                print("[!] Geen vectoren in project.")
                return

            # Toon vectoren
            for i, v in enumerate(self.vectors[:10]):
                tekst = v.get("tekst", f"Vector {i}")[:30]
                print(f"  {i + 1}. {tekst}")

            try:
                idx = int(input("\nVector nummer: ").strip()) - 1
                if 0 <= idx < len(self.vectors):
                    commentaar = input("Commentaar: ").strip()
                    if commentaar:
                        self.huidig_project["commentaren"].append({
                            "id": f"c{len(self.huidig_project['commentaren']) + 1}",
                            "type": "vector",
                            "vector_idx": idx,
                            "tekst": commentaar,
                            "datum": datetime.now().isoformat()
                        })
                        self._sla_op()
                        print("[OK] Commentaar toegevoegd!")
            except ValueError:
                print("[!] Ongeldig nummer.")

    def _view_history(self):
        """Bekijk versie historie."""
        print("\n--- VERSIE HISTORIE ---")

        if not self.huidig_project:
            print("[!] Laad eerst een project.")
            return

        versies = self.huidig_project.get("versies", [])
        if not versies:
            print("Geen versies gevonden.")
            return

        for v in versies:
            print(f"\n  Versie {v['id']}")
            print(f"  Datum: {v['datum'][:10]}")
            print(f"  Vectoren: {v['vectors_count']}")
            print(f"  {v.get('beschrijving', '')}")

    def _delete_project(self):
        """Verwijder een project."""
        print("\n--- PROJECT VERWIJDEREN ---")

        if not self.data["projecten"]:
            print("[!] Geen projecten om te verwijderen.")
            return

        print("\nProjecten:")
        for i, p in enumerate(self.data["projecten"]):
            print(f"  {i + 1}. {p['naam']}")

        try:
            idx = int(input("\nVerwijder nummer: ").strip()) - 1
            if idx < 0 or idx >= len(self.data["projecten"]):
                return

            project = self.data["projecten"][idx]
            bevestig = input(f"'{project['naam']}' verwijderen? (j/n): ").strip().lower()

            if bevestig == "j":
                # Verwijder vector file
                vector_file = self.data_dir / project["vector_file"]
                if vector_file.exists():
                    vector_file.unlink()

                self.data["projecten"].pop(idx)
                self.data["statistieken"]["totaal_projecten"] = len(self.data["projecten"])
                self._sla_op()

                if self.huidig_project and self.huidig_project["id"] == project["id"]:
                    self.huidig_project = None
                    self.vectors = []

                print(f"[OK] Project '{project['naam']}' verwijderd!")

        except (ValueError, IOError) as e:
            print(f"[!] Verwijderen mislukt: {e}")

    def _save_current_project(self):
        """Sla huidig project op."""
        if not self.huidig_project:
            return

        vector_file = self.data_dir / self.huidig_project["vector_file"]
        with open(vector_file, "w", encoding="utf-8") as f:
            json.dump({"vectors": self.vectors}, f, indent=2, ensure_ascii=False)

        # Update versie
        self.huidig_project["versies"].append({
            "id": f"v{len(self.huidig_project['versies']) + 1}",
            "datum": datetime.now().isoformat(),
            "vectors_count": len(self.vectors),
            "beschrijving": "Automatisch opgeslagen"
        })

        self.data["statistieken"]["totaal_vectors"] = sum(
            v.get("vectors_count", 0)
            for p in self.data["projecten"]
            for v in p.get("versies", [])
        )

        self._sla_op()

    # =========================================================================
    # INSTELLINGEN
    # =========================================================================

    def _instellingen_menu(self):
        """Instellingen menu."""
        print("\n--- INSTELLINGEN ---")

        print(f"\n  Data directory: {self.data_dir}")
        print(f"  Projecten: {len(self.data['projecten'])}")

        if self.huidig_project:
            print(f"\n  Huidig project: {self.huidig_project['naam']}")
            print(f"  Vectoren geladen: {len(self.vectors)}")

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _check_vectors(self, silent: bool = False) -> bool:
        """Check of er vectoren geladen zijn."""
        if not self.huidig_project:
            if not silent:
                print("[!] Laad eerst een project via menu 4.")
            return False

        if not self.vectors:
            if not silent:
                print("[!] Project heeft geen vectoren. Importeer data via menu 3.")
            return False

        return True

    def _get_vectors_from_project(self) -> list:
        """Haal vectoren uit huidig project."""
        return self.vectors if self.vectors else []
