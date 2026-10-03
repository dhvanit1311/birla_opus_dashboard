# Prime System Builder

A multi-page Streamlit prototype for **Birla Opus Prime** that turns *"buyers buy systems, not products"* into a tool.
A specifier, builder or contractor picks who they are, the project segment and the surface. The app then returns a complete
waterproofing system with a layer drawing, method statement, BOQ, TDS, CAD detail, spec text and support options.
A second section, **Project Insights**, shows the research behind the tool.

> **Prototype for illustration purposes only.** All coverage figures, prices, warranties, test values, competitor specs
> and contacts are **SAMPLE** data stored in CSV files. Generated TDS/PIS sheets carry an
> *"ILLUSTRATIVE SAMPLE – NOT AN OFFICIAL TDS"* watermark.

---

## 1. Run locally

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

The app opens at http://localhost:8501. Use Python 3.11 or newer.

## 2. Folder layout

```
app.py                      # page config, CSS, optional password gate, st.navigation
app_pages/system_builder.py # Page 1 – 6-step wizard + results, documents, enablers
app_pages/resource_centre.py# Page 2 – TDS/PIS library, sample projects, learning, sales team, FAQs
app_pages/project_insights.py# Page 3 – market, competitors, field insights, priority, roadmap, deliverables
utils/data.py               # cached CSV loaders + column validation (never crashes)
utils/ui.py                 # CSS, hero, stepper, clickable cards, chips, KPI cards, plotly template
utils/logic.py              # recommendation engine, BOQ maths, crack severity, method statement, spec text
utils/drawing.py            # isometric SVG, 2D section SVG/PNG, DXF (ezdxf), crack gauge
utils/documents.py          # DOCX / PDF / XLSX / TDS / PIS / ZIP – all generated in memory (BytesIO)
utils/state.py              # session state helpers + pop-up dialogs (support, register, layer detail)
data/*.csv                  # ALL business content – edit these, not the code
.streamlit/config.toml      # brand theme
.streamlit/secrets.toml.example
```

> The pages live in **`app_pages/`**, not `pages/`. Streamlit treats a folder called `pages/` as a legacy multipage app.
> A shared deep link such as `/project_insights` would then skip `app.py`, losing the CSS and the password gate.
> Renaming the folder avoids this.

## 3. Editing the CSV files (no coding needed)

Open any file in `data/` in Excel or Google Sheets, edit it, and save it as **CSV (UTF-8)**. Keep the header row. You can add
extra columns, but don't rename the required ones. If a file or column is missing, the app shows a yellow warning that names
the file and the expected columns, and it keeps running. Locally, changes appear on the next click or refresh.

| File | What it controls |
|---|---|
| `personas.csv` | The 3 personas. `priority_sections` (pipe-separated: `compliance`, `qa`, `cost`, `warranty`, `timeline`, `references`, `coverage`, `coats`, `tools`, `curing`, `crack`, `club`) decides what each persona sees first. `default_tab` is the panel that opens first. |
| `segments.csv` | The 9 project segments. `modifier_type` drives the logic: `repair_prep` (adds the removal + crack prep layer and makes the crack check mandatory), `low_odour`, `cpwd_spec`, `upgrade_tier`, `prefer_hdpe`, `none`. |
| `surfaces.csv` | The 11 surfaces. `needs_pressure` shows the water-pressure question; `needs_crack_check` controls the crack check. |
| `products.csv` | **Prime products only** (B30, B70, B90, C2K, C2K+, APS1, SB15, HS12, HS12S, HS15S, DST, P1K, PPS). Coverage is per unit per coat. Optional TDS columns: `tensile_mpa`, `crack_bridging_mm`, `solids_pct`, `voc_gpl`, `shelf_life_months`, `low_odour`. Blank cells print as "Illustrative value" on the TDS. |
| `generic_items.csv` | Non-branded layers (surface prep, crack filler, fibre mesh, screed, boards, tiles, backer rod) with sample rates. |
| `systems.csv` | **The recommendation table.** One row per layer, with `layer_order` going from bottom to top. Rows with the same `system_id` form one system. `condition` = `new`/`existing`/`any`; `pressure` = `none`/`positive`/`negative`/`any`. An optional `exposure_pref` (e.g. `Foot traffic`) makes that system win when the user picks that exposure. `product_code_or_generic` is either a code from `products.csv` or an item name from `generic_items.csv`. |
| `method_steps.csv` | Method statement content by `stage`. `surface` and `technology` can be `All`. Rows for a specific surface replace the `All` rows for **Testing**. `qa_check` builds the QA checklist. |
| `dos_donts.csv` | Do's and don'ts by technology (Application Steps panel). |
| `spec_templates.csv` | `standard` and `cpwd` templates. Placeholders: `{surface}`, `{surface_upper}`, `{system_name}`, `{segment}`, `{area}`, `{area_sqm}`, `{layers}`, `{layers_inline}`, `{coverage}`, `{standards}`, `{warranty}`, `{testing}`, `{tier}`, `{item_no}`. |
| `sample_projects.csv` | 12 reference projects (map and "Use this spec"). `system_id` must exist in `systems.csv`. The optional `persona` column sets the persona that "Use this spec" loads. |
| `learning_events.csv` | Workshops / CPD / site visits / applicator training (`date` as YYYY-MM-DD). |
| `sales_team.csv` | Regional technical experts (sample names and contacts). |
| `faqs.csv` | FAQ accordion. |
| `market.csv`, `segments_market.csv` | Market KPIs, TAM/SAM/SOM, treemap, growth scenario inputs. |
| `brands.csv`, `competitor_products.csv` | White-space bubble chart and the 28-product benchmark. |
| `touchpoints.csv`, `insight_links.csv`, `quotes.csv` | Field insights map, Sankey and quote cards. |
| `priority_products.csv` | 10 priority SKUs with 1–10 scores per criterion. |
| `roadmap.csv`, `scale_paths.csv`, `deliverables.csv`, `stakeholders.csv` | Gantt, scale paths, deliverables and alignment. |

**Before sharing:** P1K is described as a 1-component PU coating, and PPS is an editable placeholder. Correct both in
`products.csv` if needed. Replace sample prices and coverage with your benchmark data, or leave the SAMPLE badges visible.

## 4. Deploy to Streamlit Community Cloud

1. Push this folder to a GitHub repository. `.venv/` and `.streamlit/secrets.toml` are already in `.gitignore`.
2. Go to **share.streamlit.io**, then **Create app**, then pick the repo and branch, and set **Main file path** to `app.py`.
3. Under **Advanced settings**, choose Python **3.11** (or newer).
4. Click **Deploy**. Every later push to GitHub redeploys the app automatically, including CSV edits.

## 5. Password (optional)

If `APP_PASSWORD` exists in secrets, the app asks for it on load. Otherwise it opens directly.

- **Cloud:** App → **Settings → Secrets**, and paste `APP_PASSWORD = "your-password"`.
- **Local:** copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and set the value.

## 6. Making the app private

Streamlit Cloud links are **public by default**. If any internal numbers are in the CSVs, do one or both of these:
- set `APP_PASSWORD` (above), and/or
- go to App → **Settings → Sharing** and set **"Only specific people can view this app"**, then invite viewers by email.

## 7. Notes on behaviour

- Every document (DOCX, PDF, XLSX, DXF, PNG, SVG, ZIP) is generated **in memory when you click it**. Nothing is written to disk.
- "Submit" / "Register" / "Request callback" are **simulated**: you get a toast, a reference ID like `PRM-2026-04821`
  and a summary card. Nothing is sent anywhere.
- Balloons fire the first time a Project Pack is downloaded in a session.
- The touchpoint map uses free CARTO map tiles, which the viewer's browser loads from the internet. All other charts work offline.

---

## 8. 12-point test checklist (do this before sharing the link)

1. **Load and gate.** Open the app. The amber prototype banner and purple hero show on every page. If `APP_PASSWORD` is set, a wrong password shows an error and the right one opens the app.
2. **Persona cards.** Click each of the 3 persona cards; a click anywhere on the card works. The stepper moves to 2 and the sidebar shows the persona. Use **Edit** in the sidebar to go back and switch persona.
3. **Segments.** Click all 9 segment tiles in turn (use **Back** between them). For Repair and CHS, step 3 shows the "crack check is mandatory" note.
4. **Surfaces.** Click all 11 surface tiles. Basement, Foundation, Retaining wall, Water tank and Swimming pool show the **Water pressure** question in step 4; the others don't. Bathroom and Other wet areas show the **floors/units multiplier**.
5. **Site form.** Toggle *Enter sq ft* / *Length × Width* and check that the total area updates live. Move the crack-width slider through 0.2 / 0.6 / 2 / 4 mm: the badge goes Hairline (green), Fine (amber), Medium (orange), Structural (red, "refer to a structural engineer"), and the gauge highlights each band. For Repair/CHS, **Get my system** is blocked until "I have measured the cracks" is ticked.
6. **Results by persona.** Builder sees ₹/sq ft, total, warranty, timeline and reference projects, and BOQ opens first. PMC sees compliance chips and the QA checklist, and Method Statement opens first. Contractor sees coverage, coats, curing, tools, crack check and the Applicator Club card, and Application Steps opens first.
7. **Drawing, layers and tiers.** Click each layer pill: a dialog shows the code, what it does, coverage, coats, times and a working **Download TDS**. Switch Good / Better / Best: the drawing, chips, numbers and system name change. Open **Compare tiers**.
8. **Key logic paths.** (a) New construction → Basement → New → Better gives **HS12S** pre-applied HDPE. (b) Basement + *Negative side* gives **C2K+** inner guard. (c) Terrace + *Foot traffic* + Best gives **P1K**. (d) Government segment → Spec / Tender Text includes the **CPWD-style item description**. (e) Repair segment adds the "Remove loose coating + crack treatment" layer and the "Before you start" alert. (f) C&I defaults one tier higher.
9. **Document panels.** Open each panel button. Method Statement: download DOCX and PDF. BOQ: edit wastage/coats/rate, check that totals and the donut update, change the labour rate, and download XLSX (open it and check the formulas) and PDF. TDS: Preview shows page 1 and the PDF downloads. CAD: download PNG / SVG / DXF (open the DXF in a CAD viewer), and **Request BIM file** opens a prefilled support form. Spec: the copy button works and the .txt downloads. Application Steps: the cards and tool checkboxes render.
10. **Project Pack and support.** Download the ZIP: balloons fire the first time, and the ZIP contains the cover sheet, method statement PDF, BOQ XLSX, TDS PDFs, DXF and spec. **Get Support**: submitting shows a toast, a `PRM-…` reference and a summary; **Join WhatsApp Tech Community** shows the QR placeholder. Test the persona card buttons (Register interest / Request warranty details / Book a CPD session).
11. **Key enablers and Resource Centre.** On results: **Sample projects** opens inline specs, and **Use this spec** loads them. The TDS, Learning and Sales cards jump to the matching Resource Centre tab. In the Resource Centre: filter and search the library, Preview / TDS / PIS / **Download all (ZIP)**; filter the project map, **View spec** and **Use this spec** (switches to the System Builder results); **Register** on an event and the in-house session form; **Request callback** and **Email** on each region; open all FAQs.
12. **Project Insights.** Market: move the CAGR and share sliders and check the line and the FY27 plan message. Competitors: bubble chart with the today → target arrow, filter the benchmark table by player, and the scatter. Field Insights: map, Sankey, 3 insight cards, 6 quotes. Product Priority: move the weights and check that the ranking and stacked bars re-order. GTM: 5 lever cards, Gantt with the Today line, scale-path table. Deliverables: status pills and the % closed ring. Finally, open a deep link (e.g. `/project_insights`) in a new browser tab and check that styling, the banner and the password gate still apply.
