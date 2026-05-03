# Shopify Analytics Chatbot MVP Plan

## Document Purpose

This document is the build spec for a lightweight but intelligent analytics chatbot over Shopify Excel data. It is designed to be fed into an MCP client or development agent as a complete implementation blueprint.

The goal is not to build a generic chatbot. The goal is to build a **schema-aware analytical assistant** that can:

- understand natural language questions,
- infer the correct tables and joins,
- generate safe SQL,
- execute the query over Excel-loaded tables,
- compute derived metrics,
- explain how the answer was produced,
- recover from query errors,
- and do all of this with very limited infrastructure.

This is intentionally an MVP, but a very sharp one. The system should feel smart, reliable, and traceable, without becoming overengineered.

---

# 1. Product Definition

## 1.1 One-line definition

A schema-aware analytical chatbot that converts natural language into executable SQL over Excel-based Shopify tables, with join reasoning, derived metrics, and automatic query repair.

## 1.2 Problem statement

The stakeholder wants a chatbot that can answer questions from a Shopify dataset spread across multiple Excel sheets. Some questions will require:

- joining multiple tables,
- aggregating across rows,
- comparing time windows,
- calculating derived business metrics,
- and explaining the result.

This is not a retrieval-only problem. It is a **data reasoning** problem.

## 1.3 What the system must do

The system must:

- ingest an Excel workbook with multiple sheets,
- treat each sheet as a relational table,
- infer schema and relationships,
- translate natural language to structured analytical intent,
- compile that intent into SQL,
- run the SQL in DuckDB,
- format a response that a non-technical user can understand,
- show evidence of how the answer was produced,
- and handle failing queries gracefully.

## 1.4 What the system should not do in MVP

Avoid these in the first version:

- full RAG over sheet chunks,
- heavyweight multi-agent orchestration,
- vector database over every row,
- free-form Python code execution from model output,
- enterprise auth,
- session persistence beyond basic in-memory storage,
- full-fledged dashboarding,
- long-term memory over many conversations.

The MVP should optimize for **accuracy, traceability, and speed of delivery**.

---

# 2. Core Architectural Decision

## 2.1 Final approach

The recommended architecture is:

**User Query → Planner → Structured JSON Plan → SQL Compiler → SQL Validator → DuckDB Executor → Answer Formatter → Explanation Panel**

If the query fails:

**DuckDB Error → Repair Prompt → LLM Fix → Re-validate → Re-execute**

This pipeline is the center of the product.

## 2.2 Why this architecture is the right fit

This approach works because the problem is fundamentally relational.

A row retrieval model is weak for:

- multi-table joins,
- group-by analytics,
- time comparisons,
- revenue calculations,
- top-N analysis,
- and derived metrics.

SQL is the correct execution layer. DuckDB is the correct lightweight engine. The LLM should act as the planner and translator, not as the database.

## 2.3 Why not pure RAG

RAG is a mismatch here because:

- it does not naturally handle joins,
- it is poor for exact arithmetic,
- it is weak for aggregation logic,
- and it is not reliable for time-window comparisons.

RAG can help with metadata or documentation, but not as the core analytical engine.

## 2.4 Why not Pandas-only agent

A Pandas-based code generation approach can work, but it is less safe and less stable.

Problems:

- generated Python can be brittle,
- joins can become messy,
- debugging is harder,
- code execution has more surface area for failure.

Pandas can remain a fallback or internal utility, but not the main architecture.

---

# 3. Product Principles

The system should follow these principles:

1. **SQL-first analytics**
   - The model should reason about relational data, not freestyle answers.

2. **Structured planning before execution**
   - Every query should first become a plan.

3. **Safe execution**
   - Only read-only operations.

4. **Traceability**
   - Show the generated SQL, tables used, and formula applied.

5. **Lean MVP**
   - Keep the implementation small enough to finish cleanly.

6. **Repairability**
   - Query errors should be recoverable automatically.

7. **Business language understanding**
   - Terms like revenue, AOV, growth, and drop should be interpreted correctly.

8. **Explainability**
   - Every answer should be interpretable by the user.

---

# 4. Recommended Stack

## 4.1 Backend

- **FastAPI** for API endpoints
- **Pydantic** for request/response schemas
- **DuckDB** for analytical SQL execution
- **Pandas** for Excel ingestion and lightweight transformations
- **sqlglot** or similar for SQL parsing and validation
- **OpenAI API** or a local LLM for planning and SQL generation

## 4.2 Frontend

- **Streamlit** for fastest MVP delivery

Optionally:

- **Next.js** only if a polished UI becomes important later

For this task, Streamlit is the best tradeoff.

## 4.3 Data layer

- Excel workbook ingestion via **pandas** and **openpyxl**
- Tables stored in **DuckDB**
- Optional **Parquet cache** for future optimization

## 4.4 Reasoning layer

- Structured JSON planning
- Business glossary resolution
- Query repair loop
- Explanation generation

## 4.5 Why this stack is optimal

This stack is ideal because it is:

- easy to ship,
- cheap to run,
- good for joins and analytics,
- simple to explain in an interview,
- and strong enough to feel production-minded.

---

# 5. Scope Philosophy

## 5.1 What the MVP should prove

The MVP should prove that the system can:

- understand a business question,
- identify the right tables,
- generate correct joins,
- compute derived metrics,
- compare time periods,
- and explain the answer.

## 5.2 What the MVP should intentionally avoid

Do not overbuild:

- no universal schema discovery engine,
- no full autonomous agent swarm,
- no fancy memory architecture,
- no multi-database abstraction,
- no complex workflow engine.

## 5.3 The strongest idea for this project

The strongest idea is not “chat with data.”

The strongest idea is:

> “A schema-aware analytical copilot that converts natural language into validated SQL and can explain exactly how each result was derived.”

That is much stronger than a generic chatbot.

---

# 6. System Overview

## 6.1 Main flow

1. User enters a question.
2. The system analyzes intent.
3. The system builds a structured plan.
4. The plan is converted into SQL.
5. SQL is validated for safety.
6. DuckDB executes the SQL.
7. Results are formatted.
8. A reasoning/explanation panel is generated.
9. If the SQL fails, the system repairs and retries once.

## 6.2 Core data flow diagram

```text
User Query
  ↓
Intent + Entity Extraction
  ↓
Structured JSON Plan
  ↓
SQL Compiler
  ↓
SQL Validator
  ↓
DuckDB Executor
  ↓
Result Formatter
  ↓
Answer + Explanation
```

## 6.3 Repair flow

```text
SQL Error
  ↓
Error Analysis Prompt
  ↓
LLM SQL Fix
  ↓
Validation
  ↓
Re-execution
```

This is one of the key differentiators.

---

# 7. Data Understanding Strategy

## 7.1 Excel workbook as the source of truth

Each sheet in the workbook should be treated as a table.

Example:
- `products`
- `orders`
- `order_line_items`
- `customers`
- `refunds`
- `discounts`

The workbook structure may vary slightly, but the system should normalize the names and infer the schema.

## 7.2 Sheet normalization

Each sheet name should be normalized into SQL-safe table names:

- lowercase
- spaces to underscores
- remove symbols
- standardize plurals if needed

Examples:
- `Order Line Item` → `order_line_items`
- `Product Details` → `product_details`

## 7.3 Column normalization

Column names should also be normalized:

- lowercase
- spaces to underscores
- remove punctuation
- standardize duplicate names

Examples:
- `Created At` → `created_at`
- `Product ID` → `product_id`
- `Order Amount` → `order_amount`

## 7.4 Type inference

Infer column types:

- date/time → timestamp or date
- numeric strings → integer/float
- booleans → boolean
- IDs → text or integer depending on source
- free text → varchar

Type inference matters because the LLM will need accurate schema context and SQL operators must match types.

---

# 8. Schema Intelligence Layer

This layer is essential.

The system should not just know tables exist. It should know what they mean.

## 8.1 What schema intelligence contains

For each table:

- table name
- description
- column names
- column types
- sample values
- primary key candidates
- foreign key candidates
- likely metric columns
- likely date columns
- likely join relationships

## 8.2 Schema registry object

This should be stored in a structured format.

Example:

```json
{
  "table_name": "order_line_items",
  "description": "Each row represents a product sold on an order.",
  "columns": [
    {"name": "order_id", "type": "integer", "role": "foreign_key"},
    {"name": "product_id", "type": "integer", "role": "foreign_key"},
    {"name": "quantity", "type": "integer", "role": "measure"},
    {"name": "price", "type": "decimal", "role": "measure"}
  ],
  "sample_rows": [
    {"order_id": 101, "product_id": 15, "quantity": 2, "price": 499.0}
  ]
}
```

## 8.3 Minimal schema intelligence functions

The MVP should include:

- `inspect_schema()`
- `normalize_table_names()`
- `normalize_column_names()`
- `infer_column_types()`
- `sample_table_rows()`
- `detect_candidate_keys()`
- `map_relationships()`
- `build_schema_registry()`

## 8.4 Hardcoded relationships for MVP

A crucial simplification:

Do **not** overinvest in automatic join-graph discovery if the workbook structure is known.

Hardcode likely Shopify relationships such as:

- `orders.order_id` → `order_line_items.order_id`
- `products.product_id` → `order_line_items.product_id`
- `customers.customer_id` → `orders.customer_id`

This is a smart scope cut.

It removes complexity while preserving analytical power.

## 8.5 Why hardcoding relationships is acceptable

For a timed skill test, precision is better than abstraction.

Hardcoding the known business relationships:

- reduces errors,
- simplifies the compiler,
- speeds up development,
- and makes the demo more reliable.

---

# 9. Business Glossary Layer

## 9.1 Purpose

Users ask business questions, not database questions.

The glossary translates business language into expressions.

## 9.2 Glossary examples

- revenue = `quantity * price`
- total sales = `sum(quantity * price)`
- orders count = `count(distinct order_id)`
- AOV = `revenue / orders_count`
- revenue drop = `current_period_revenue - previous_period_revenue < 0`
- top products = rank by revenue or units sold

## 9.3 Glossary functions

- `build_glossary()`
- `resolve_business_term(term)`
- `get_metric_expression(metric_name)`
- `resolve_time_window(term)`

## 9.4 Why glossary matters

Without a glossary, the model may understand SQL but miss the business meaning.

For example:

- “revenue” might not appear as a column,
- “AOV” may need to be derived,
- “drop” may imply comparison against a prior period.

The glossary converts fuzzy business language into deterministic computations.

---

# 10. Query Planning Layer

This is the brain of the system.

## 10.1 Why planning comes before SQL

The model should not jump directly to SQL because that produces brittle and hard-to-debug outputs.

Instead, it should first create a plan.

The plan should say:

- what the user wants,
- which tables are needed,
- what the join path is,
- what metrics must be computed,
- what time windows apply,
- and what the final output should look like.

## 10.2 Planner output format

The planner should return strict JSON.

Example:

```json
{
  "intent": "compare_revenue_between_days",
  "tables_needed": ["products", "orders", "order_line_items"],
  "join_paths": [
    {
      "left_table": "orders",
      "left_column": "order_id",
      "right_table": "order_line_items",
      "right_column": "order_id"
    },
    {
      "left_table": "products",
      "left_column": "product_id",
      "right_table": "order_line_items",
      "right_column": "product_id"
    }
  ],
  "filters": [
    {
      "table": "orders",
      "column": "created_at",
      "operator": "date_equals",
      "value": "yesterday"
    }
  ],
  "metrics": [
    {
      "name": "revenue",
      "expression": "quantity * price"
    }
  ],
  "group_by": ["products.product_name"],
  "output_columns": ["product_name", "revenue_today", "revenue_yesterday", "delta"]
}
```

## 10.3 Planner function

Main function:

- `build_query_plan(user_query, schema_context, glossary_context)`

Additional helper functions:

- `classify_intent(query)`
- `extract_entities(query)`
- `detect_time_reference(query)`
- `detect_metric_reference(query)`
- `detect_comparison_reference(query)`
- `detect_grouping_reference(query)`

## 10.4 Intent categories

The planner should classify requests into a small number of types:

- simple lookup
- aggregation
- comparison
- trend analysis
- top-N ranking
- join-based lookup
- derived metric calculation
- anomaly/drop detection

This makes routing easier.

## 10.5 Why JSON planning is powerful

JSON planning is valuable because it:

- reduces hallucination,
- makes debugging easier,
- separates reasoning from execution,
- and allows validation before SQL generation.

This is one of the biggest indicators of senior-level thinking in the project.

---

# 11. SQL Compilation Layer

## 11.1 Purpose

The compiler turns the plan into executable SQL.

## 11.2 Responsibilities

The compiler must:

- write SELECT queries,
- add joins,
- apply filters,
- apply grouping,
- generate derived metrics,
- handle time windows,
- alias columns consistently,
- and keep the SQL readable.

## 11.3 Compiler functions

- `compile_plan_to_sql(plan)`
- `build_select_clause(plan)`
- `build_from_and_joins(plan)`
- `build_where_clause(plan)`
- `build_group_by_clause(plan)`
- `build_order_by_clause(plan)`
- `build_cte_for_time_comparison(plan)`

## 11.4 SQL style guidelines

The SQL should be:

- readable,
- CTE-friendly,
- deterministic,
- and safe.

Prefer CTEs for clarity when a query becomes complex.

## 11.5 Example compiler behavior

For a query like:

> Which products witnessed a revenue drop yesterday?

The compiler should generate something that compares revenue across two time windows and groups by product.

## 11.6 SQL output requirements

The SQL must:

- use only known tables,
- use only known columns,
- return only SELECT statements,
- avoid destructive commands,
- and be valid in DuckDB.

---

# 12. SQL Validation Layer

Validation is not optional.

## 12.1 Validation checks

Before execution:

- SQL must begin with `SELECT` or `WITH`
- no `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`
- all tables must exist in schema registry
- all columns must exist in referenced tables
- aliases must be defined properly
- group-by logic must be coherent
- date functions must be compatible with DuckDB

## 12.2 SQL validation functions

- `parse_sql(sql)`
- `validate_sql(sql, schema_registry)`
- `enforce_read_only_sql(sql)`
- `resolve_identifiers(sql, schema_registry)`
- `check_group_by_consistency(sql)`

## 12.3 Why validation matters

This reduces errors, prevents unsafe queries, and makes the system much more reliable.

---

# 13. DuckDB Execution Layer

## 13.1 Why DuckDB

DuckDB is the best fit because it is:

- lightweight,
- fast,
- local,
- analytical,
- and easy to integrate with Excel-derived tables.

It is a perfect choice for a small but powerful MVP.

## 13.2 Execution functions

- `create_duckdb_connection()`
- `load_tables_into_duckdb()`
- `execute_sql(sql)`
- `execute_sql_with_timeout(sql, seconds)`
- `preview_sql_results(sql, limit)`
- `fetch_dataframe(sql)`

## 13.3 Data storage mode

Preferred mode for MVP:

- load data from Excel into DuckDB tables at startup,
- keep the database in memory or as a local file,
- optionally persist to a `.duckdb` file for reuse.

## 13.4 Execution safeguards

- set a query timeout,
- cap returned rows,
- restrict to read-only queries,
- catch exceptions cleanly.

---

# 14. Repair Loop

This is one of the strongest differentiators.

## 14.1 Problem it solves

Even a good model will sometimes:

- use the wrong column name,
- choose the wrong date function,
- make a join error,
- forget to group by properly,
- or produce syntax not supported by DuckDB.

The repair loop fixes this.

## 14.2 Repair loop flow

1. Execute SQL.
2. If it fails, capture the error.
3. Pass the error, schema, and original plan to the LLM.
4. Ask for corrected SQL only.
5. Validate again.
6. Re-execute once.

## 14.3 Repair function

- `repair_sql(original_sql, error_message, schema_context, original_plan)`

## 14.4 Repair prompt requirements

The repair prompt should say:

- fix the query,
- preserve user intent,
- do not introduce new tables unless clearly needed,
- output only SQL,
- do not explain in prose.

## 14.5 Why repair loop matters

This is the kind of feature interviewers like because it shows resilience, not just generation.

It turns a brittle demo into a system that can self-correct.

---

# 15. Answer Formatting Layer

## 15.1 Why formatting matters

Raw data is not an answer.

The user wants a result that is understandable and useful.

## 15.2 Formatter responsibilities

The formatter should:

- summarize the result,
- present key rows,
- highlight the main conclusion,
- mention derived metrics,
- show a compact preview table when relevant,
- and keep the answer concise.

## 15.3 Formatter function

- `format_answer(result_df, query, metadata)`

## 15.4 Response style

Responses should be:

- short,
- direct,
- business-oriented,
- and trustworthy.

## 15.5 Example answer components

A response can include:

- the conclusion,
- the computed values,
- the tables used,
- and a traceability note.

---

# 16. Explanation and Traceability Panel

This is a high-value differentiator.

## 16.1 What to show

The UI should include a small panel explaining:

- SQL generated,
- tables joined,
- formula used,
- filters applied,
- and maybe why the result is trustworthy.

## 16.2 Why it matters

Interviewers and evaluators care about traceability.

A bot that can show **how** it got the answer looks much more mature than one that simply prints a response.

## 16.3 Explanation function

- `generate_explanation(plan, sql, result_summary)`

## 16.4 Suggested explanation format

- joined tables used
- metric formula
- time filter logic
- result interpretation

## 16.5 Optional confidence indicator

Add a small badge such as:

- `Simple query`
- `2-table join`
- `Complex query`
- `Derived metric + comparison`

This subtly communicates how much reasoning was needed.

---

# 17. Frontend Plan

## 17.1 MVP frontend choice

Use **Streamlit**.

Why:

- fastest to build,
- easy to demo,
- clean for internal evaluation,
- no need for routing or complex frontend state.

## 17.2 UI layout

Recommended layout:

### Main area
- chat input
- answer output
- result table preview
- SQL preview
- explanation panel

### Sidebar
- dataset schema summary
- sample prompts
- query type badge
- system status

## 17.3 UI components

- chat input box
- submit button
- response container
- SQL viewer
- dataframe preview table
- schema browser
- suggested query buttons

## 17.4 What the UI should not try to do

Avoid:

- elaborate multi-page workflows,
- complicated charts on day one,
- deep user management,
- unnecessary styling work.

The UI should be clean and functional.

---

# 18. API Design

## 18.1 Endpoint list

### `POST /chat`
Main endpoint for user questions.

### `GET /schema`
Returns all tables, columns, sample values, and relationships.

### `POST /reload-data`
Reloads the Excel workbook.

### `GET /health`
Health check.

### `GET /history/{session_id}`
Optional. Basic history only.

## 18.2 `POST /chat` request

```json
{
  "session_id": "abc123",
  "message": "Which products witnessed a revenue drop yesterday?"
}
```

## 18.3 `POST /chat` response

```json
{
  "answer": "...",
  "sql": "...",
  "tables_used": ["products", "orders", "order_line_items"],
  "explanation": "...",
  "result_preview": [...],
  "query_complexity": "Complex query · 3 tables joined"
}
```

---

# 19. Internal Modules and Functions

This section defines the full implementation map.

## 19.1 Data ingestion module

Functions:
- `load_workbook(path)`
- `read_sheet(sheet_name)`
- `normalize_dataframe(df)`
- `normalize_table_name(name)`
- `normalize_column_names(df)`
- `infer_types(df)`
- `store_to_duckdb(df, table_name)`
- `refresh_dataset()`

## 19.2 Schema module

Functions:
- `inspect_schema()`
- `get_table_schema(table_name)`
- `sample_table_rows(table_name)`
- `detect_key_candidates()`
- `build_schema_registry()`
- `build_join_map()`

## 19.3 Glossary module

Functions:
- `build_glossary()`
- `resolve_metric(term)`
- `resolve_time_phrase(term)`
- `resolve_business_term(term)`

## 19.4 Planner module

Functions:
- `classify_intent(query)`
- `extract_entities(query)`
- `detect_tables_needed(query)`
- `detect_join_requirements(query)`
- `detect_time_window(query)`
- `detect_formula_requirements(query)`
- `build_query_plan(query)`

## 19.5 SQL compiler module

Functions:
- `compile_plan_to_sql(plan)`
- `build_select_clause(plan)`
- `build_from_clause(plan)`
- `build_join_clause(plan)`
- `build_where_clause(plan)`
- `build_group_by_clause(plan)`
- `build_order_by_clause(plan)`
- `build_ctes(plan)`

## 19.6 SQL validation module

Functions:
- `parse_sql(sql)`
- `validate_sql(sql)`
- `validate_tables(sql)`
- `validate_columns(sql)`
- `validate_read_only(sql)`
- `validate_grouping(sql)`

## 19.7 Execution module

Functions:
- `execute_sql(sql)`
- `execute_sql_safe(sql)`
- `execute_sql_with_timeout(sql)`
- `fetch_df(sql)`

## 19.8 Repair module

Functions:
- `repair_sql(sql, error)`
- `repair_plan(plan, error)`
- `retry_execution(sql)`

## 19.9 Formatting module

Functions:
- `format_result(df)`
- `summarize_rows(df)`
- `build_response_payload()`
- `generate_explanation()`

## 19.10 UI module

Functions:
- `render_chat_ui()`
- `render_schema_sidebar()`
- `render_sql_viewer()`
- `render_explanation_panel()`
- `render_result_table()`

---

# 20. Prompt Engineering Spec

## 20.1 Planner prompt

The planner prompt must instruct the model to:

- output JSON only,
- infer business intent,
- identify joins,
- detect time windows,
- map metrics to formulas,
- and avoid hallucinating schema.

## 20.2 SQL generation prompt

The SQL prompt must instruct the model to:

- use only provided schema,
- output only SQL,
- use DuckDB-compatible syntax,
- include joins clearly,
- use aliases consistently,
- and compute derived metrics using glossary definitions.

## 20.3 Repair prompt

The repair prompt must instruct the model to:

- fix the SQL using the error message,
- preserve the original intent,
- and return only corrected SQL.

## 20.4 Explanation prompt

The explanation prompt must instruct the model to:

- explain the answer concisely,
- mention tables and formulas,
- and avoid unnecessary verbosity.

---

# 21. Query Types the MVP Must Support

## 21.1 Lookup queries

Example:
- Which product had the highest sales?

## 21.2 Aggregation queries

Example:
- What is total revenue by product category?

## 21.3 Join queries

Example:
- Which customers bought product X last week?

## 21.4 Comparison queries

Example:
- Which products witnessed a revenue drop yesterday?

## 21.5 Derived metric queries

Example:
- What is the AOV for each order?

## 21.6 Top-N ranking queries

Example:
- Show top 10 products by revenue.

## 21.7 Trend queries

Example:
- What is daily revenue over the last 30 days?

---

# 22. Query Example Walkthrough

## 22.1 Example question

> Which products witnessed a revenue drop yesterday?

## 22.2 What the system should infer

- The user wants a comparison across time.
- Revenue must likely be derived.
- Product-level grouping is needed.
- Multiple tables are required.
- The answer should compare yesterday vs the previous period.

## 22.3 Likely tables used

- `products`
- `orders`
- `order_line_items`

## 22.4 Likely metric formula

`revenue = quantity × price`

## 22.5 Output structure

- product name
- revenue yesterday
- revenue previous day
- delta
- result summary
- explanation

## 22.6 Why this query is valuable

This query demonstrates exactly the skills the evaluator wants to see:

- natural language understanding,
- joins,
- arithmetic,
- temporal reasoning,
- and explanation.

---

# 23. Confidence and Complexity Layer

## 23.1 Why this helps

A small signal that reflects query complexity makes the system feel more intelligent.

## 23.2 Possible labels

- Simple lookup
- 1-table aggregate
- 2-table join
- 3-table join
- Derived metric
- Comparison query
- Complex analytical query

## 23.3 Complexity function

- `estimate_query_complexity(plan)`

This can be used for display only.

---

# 24. Error Handling Strategy

## 24.1 Types of expected errors

- missing column name
- wrong join key
- invalid type comparison
- unsupported date syntax
- empty result set
- division by zero
- ambiguous intent

## 24.2 Error handling behavior

The system should:

- capture the error,
- classify it,
- optionally repair the SQL,
- and provide a user-friendly fallback if still failing.

## 24.3 Fallback response pattern

If the query cannot be answered reliably, respond with:

- what was attempted,
- what failed,
- and a clarification question or a safe fallback.

---

# 25. Logging and Debugging

## 25.1 What to log

- user query
- parsed plan
- generated SQL
- execution time
- errors
- retry attempts
- result row count

## 25.2 Why logs matter

Logs help with:

- debugging,
- demo validation,
- and explaining query decisions later.

## 25.3 Lightweight logging approach

Use simple structured logs in JSON or console output.

Do not overinvest in observability tooling for MVP.

---

# 26. Testing Plan

## 26.1 Unit tests

Test:

- schema normalization,
- glossary resolution,
- planner JSON format,
- SQL generation,
- SQL validation,
- formatter output.

## 26.2 Integration tests

Test end-to-end queries such as:

- revenue drop yesterday,
- top products by revenue,
- AOV by customer segment,
- revenue trend by day.

## 26.3 Edge case tests

- blank query,
- unknown term,
- invalid date phrase,
- missing join column,
- no-result query,
- ambiguous question.

## 26.4 Demo test set

Prepare 5–8 strong prompts that demonstrate the system well.

Focus on:

- joins,
- derived metrics,
- comparisons,
- and explanation.

---

# 27. Recommended Build Scope by Priority

## Tier 1 — Must build

- Excel ingestion into DuckDB
- schema registry
- hardcoded known relationships
- planner JSON output
- SQL compiler
- SQL validation
- DuckDB executor
- Streamlit chat UI
- answer formatting
- explanation panel

## Tier 2 — Strong differentiators

- repair loop
- business glossary
- derived metrics
- query complexity badge
- SQL preview

## Tier 3 — Optional if time remains

- history panel
- schema browser UI
- charts
- saved queries
- result export

## Tier 4 — Skip in MVP

- Next.js frontend
- vector database
- full join graph auto-discovery
- long-term memory
- full agent orchestration framework
- extensive test harness beyond essentials

---

# 28. Development Phases

## Phase 1 — Data foundation

Deliverables:

- workbook ingestion
- normalized table and column names
- DuckDB loading
- schema registry

## Phase 2 — Reasoning foundation

Deliverables:

- glossary
- planner JSON schema
- prompt design
- sample schema context generation

## Phase 3 — Execution foundation

Deliverables:

- SQL compilation
- validation layer
- query execution
- result formatting

## Phase 4 — Smartness layer

Deliverables:

- repair loop
- derived metrics
- time reasoning
- traceability panel

## Phase 5 — UI polish

Deliverables:

- Streamlit UI
- sample prompt buttons
- query preview
- explanation view

## Phase 6 — Final hardening

Deliverables:

- demo query set
- edge-case testing
- performance check
- final narrative for presentation

---

# 29. Suggested Timeline for a Fast MVP

## Day 1
- inspect workbook
- identify tables and columns
- normalize names
- load into DuckDB

## Day 2
- build schema registry
- define hardcoded Shopify relationships
- confirm sample joins manually

## Day 3
- build planner prompt
- define JSON schema
- wire planner output to backend

## Day 4
- build SQL compiler
- validate generated SQL
- confirm it runs on DuckDB

## Day 5
- add repair loop
- add explanation generation
- add business glossary

## Day 6
- build Streamlit UI
- show SQL, result, explanation
- add sample prompts

## Day 7
- test edge cases
- tune prompts
- prepare demo script
- finalize response examples

---

# 30. Deliverables Checklist

## Code deliverables

- backend service
- data ingestion module
- planner module
- SQL compiler module
- validation module
- executor module
- repair module
- UI app

## Documentation deliverables

- architecture overview
- schema map
- prompt spec
- function map
- test cases
- demo instructions
- known limitations

## Demo deliverables

- working chat interface
- 3–5 strong example questions
- visible SQL output
- visible result table
- visible explanation panel

---

# 31. Acceptance Criteria

The MVP is successful if it can reliably answer questions like:

- Which products witnessed a revenue drop yesterday?
- What are the top 5 products by revenue this week?
- What is AOV by customer segment?
- Which orders have the highest total value?
- What is daily revenue over the last 30 days?

A good result is one that:

- uses correct tables,
- joins correctly,
- computes derived metrics correctly,
- returns stable output,
- and explains the result clearly.

---

# 32. Final Recommendation

## Final stack

- **FastAPI**
- **DuckDB**
- **Pandas**
- **OpenAI structured outputs or local LLM**
- **sqlglot**
- **Streamlit**
- **Pydantic**

## Final architecture

**Planner → SQL Compiler → DuckDB Executor → Repair Loop → Answer Formatter → Explanation Panel**

## Final scope advice

Keep it lean.

Do not overbuild the join discovery logic.
Hardcode the known Shopify relationships.
Build the core loop first.
Make the answer traceable.
Make the SQL valid.
Make the repair loop work.
That is what will impress.

---

# 33. Final Positioning Statement

Use this to describe the project:

> I built a schema-aware analytical chatbot that converts natural language into validated SQL over Excel-based Shopify data, supports multi-table joins and derived metrics, and can repair queries automatically when execution fails.

That is the cleanest description of the solution.

---

# 34. Optional Implementation Notes for MCP

If this file is consumed by an MCP client or coding agent, instruct it to follow these rules:

1. Implement the data foundation first.
2. Validate the schema before any LLM integration.
3. Hardcode known table relationships.
4. Use strict JSON for planner output.
5. Compile SQL only from validated plan objects.
6. Run all SQL through a read-only guard.
7. Add the repair loop before UI polish.
8. Keep the UI minimal and functional.
9. Document every function and prompt.
10. Prefer correctness over breadth.

---

# 35. End State

When complete, this system should feel like a small analytical copilot:

- users ask business questions in plain English,
- the system reasons over tables,
- produces SQL,
- executes safely,
- explains itself,
- and repairs failures.

That is the exact balance of small, smart, and impressive.

