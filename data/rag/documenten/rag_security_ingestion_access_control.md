# RAG Security: Data Ingestion & Access Control Guide

This guide outlines the security evolution of a RAG system, from a basic prototype to a bank-grade enterprise architecture. It covers Data Ingestion (getting data in safely) and Access Control (ensuring only the right people see it).

## Part 1: Data Ingestion & Processing

The goal: Ensure that what enters your system is clean, safe, and privacy-compliant.

### Level 1: Beginner (The "Clean Prototype")

At this stage, your focus is simply on preventing garbage in/garbage out and basic hygiene.

**Rule 1: Sanitation.** Strip HTML tags, weird unicode characters, and system headers/footers before embedding. These confuse the LLM.

**Rule 2: Basic Exclusion.** Hard-code a "deny list" of file types. Do not ingest .exe, .zip, or system files.

**Rule 3: Secrets Filtering.** Run a regex scan for simple patterns like `sk-live-...`, `AWS_ACCESS_KEY`, or `BEGIN RSA PRIVATE KEY` and drop those chunks immediately.

### Level 2: Intermediate (The "Privacy-Aware App")

You are now handling real user data. Compliance (GDPR/CCPA) becomes critical.

**Rule 1: PII Redaction.**
Use tools like Microsoft Presidio or GLiNER to detect and redact sensitive entities (Names, SSNs, Emails).

- **Technique**: Replace specific values with generic tokens (`<PERSON>`, `<EMAIL>`).

**Rule 2: Malware Scanning.** Scan every file before it touches your parsing logic. A malicious PDF (e.g., via PDFex) can exploit your ingestion library to steal server keys.

**Rule 3: OCR Security.** If parsing images/scans, use a sandboxed OCR engine. Malformed image headers can trigger buffer overflows in standard libraries like libtesseract.

### Level 3: Specialist (The "Fort Knox Enterprise")

At this level, "redaction" isn't enough; you need to preserve data utility while guaranteeing zero leakage.

**Rule 1: Entity-Linked Anonymization.**

- **Problem**: Standard redaction breaks context. "John sued Jane" becomes "PERSON sued PERSON." The LLM loses track of who is who.
- **Solution**: Use consistent hashing or entity linking. "John" becomes `Person_A` and "Jane" becomes `Person_B` throughout the document. The LLM understands the relationship without knowing the identity.

**Rule 2: Cryptographic Lineage.** Sign every chunk with a digital signature during ingestion. If a rogue admin modifies a vector directly in the DB to inject false info (poisoning), the signature verification fails during retrieval.

**Rule 3: The "Delta Sync" Pipeline.** Real-time syncing. If a file is deleted in SharePoint, its vectors must be deleted instantly.

- **Implementation**: Use a Change Data Capture (CDC) connector that listens to the source system's event log, rather than running a nightly batch job.

## Part 2: Document-Level Access Control (ACLs)

The goal: "User A" must never see "User B's" private documents in the answer.

### Level 1: Beginner (Metadata Tagging)

You rely on the honor system or simple application logic.

- **Mechanism**: Add a metadata field to your vector: `{"department": "marketing"}`.
- **Retrieval**: When a user queries, your code adds a filter: `.filter(department="marketing")`.
- **The Risk**: If a developer forgets to add the filter in one API endpoint, data leaks. This is "Security by Convention" (weak).

### Level 2: Intermediate (RBAC & Pre-Filtering)

You integrate with your company's Identity Provider (IdP) like Active Directory or Okta.

**Rule 1: Flattening Permissions.**

- Source systems (Google Drive, SharePoint) have hierarchical permissions (Folder A > Subfolder B). Vector DBs are flat.
- **Action**: During ingestion, calculate the effective list of allowed groups for a document and stamp it on every chunk: `access_control_list: ["group_engineering", "user_alice"]`.

**Rule 2: Pre-Filtering (The Golden Standard).**

- Never retrieve 100 docs and then check if the user can see them (Post-filtering). You might filter out all 100 and return nothing, or worse, leak data.
- **Action**: Push the filter into the vector search query. The database only searches vectors where `user_groups INTERSECT chunk_acls` is not empty.

### Level 3: Specialist (ABAC & Dynamic Policy)

For banks, defense, and healthcare. Roles aren't enough; context matters.

**Rule 1: Attribute-Based Access Control (ABAC).**

- **Scenario**: "Analysts can read 'Top Secret' docs, but ONLY from the office IP and ONLY during work hours."
- **Implementation**: You cannot stamp this on the static vector. You need an external policy engine (like OPA - Open Policy Agent) that evaluates the request context before constructing the database query.

**Rule 2: Handling "Stale" Permissions.**

- **The Problem**: Alice moves from HR to Sales. AD is updated, but the Vector DB still has her old permissions stamped on millions of chunks. Re-indexing takes days.
- **Solution**: Late-Binding ACLs. Store a "Document ID" in the vector DB, but keep the ACLs in a fast, separate lookup store (like Redis).
  1. Vector DB finds top 100 Document IDs (no filtering yet).
  2. App checks Redis: "Does Alice have access to these IDs right now?"
  3. Filter and rerank.
- **Trade-off**: Slightly slower than pre-filtering, but guarantees instant security updates.
