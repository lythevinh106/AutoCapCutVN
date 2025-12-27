---
trigger: manual
---

Đây là file hướng dẫn **Markdown (.md)** được tối ưu hóa để Agent (như Vibe Code, Cursor, Copilot...) có thể đọc hiểu và thực thi quy trình "End-to-End" từ lúc quét Draft cho đến khi cập nhật API Document.

Bạn hãy lưu nội dung bên dưới thành file **`AGENT_TASK_IMPLEMENT_FEATURE.md`** trong thư mục dự án của bạn.

---

# 🤖 AGENT TASK: Implement New CapCut Feature

**Objective:** This protocol defines the workflow to implement a new resource type (e.g., Fonts, Animations, Stickers) by synchronizing data from a CapCut draft, updating the sync script, implementing the server endpoint, and updating documentation.

**Trigger Command:** `implement [JSON_KEY] -> [TARGET_META_FILE]`
*(Example: `implement texts/fonts -> font_meta.py`)*

## 📦 Phase 1: Resource Analysis & Validation

1. **Locate Configuration:**
* Read the existing `sync_script.py` (or the main script provided in context).
* Extract variables:
* `DRAFT_FOLDER`: (e.g., `C:\Users\VINH\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft`)
* `DRAFT_NAME`: (e.g., `"effect_library"`)




2. **Analyze Draft JSON:**
* Construct path: `os.path.join(DRAFT_FOLDER, DRAFT_NAME, "draft_content.json")`.
* Load the JSON content (handle Gzip if necessary).


3. **Verify Data Existence (CRITICAL):**
* Search the JSON `materials` object for the **[JSON_KEY]** requested by the user (e.g., `texts`, `material_animations`, `stickers`).
* **Logic:**
* **IF** the key exists AND is not empty: Proceed to Phase 2.
* **IF** the key is missing or empty: **STOP**. Return a message: *"⚠️ Resource [JSON_KEY] not found in draft 'effect_library'. Skipped implementation."*





## 🛠️ Phase 2: Update Sync Script (`sync_resources.py`)

1. **Define Target Metadata File:**
* Identify `METADATA_DIR/pycapcut/metadata/[TARGET_META_FILE]`.
* Ensure the file exists or create it with standard imports.


2. **Implement Code Generator:**
* Create a specific `generate_[type]_code` function in the sync script.
* **Mapping Rules:**
* Extract `name`, `resource_id`, `effect_id`.
* Format as Python code: `VAR_NAME = MetaClass("Name", is_vip, "ID", ...)`
* Ensure variable names are sanitized (no special chars).




3. **Inject Sync Logic:**
* In the `sync_all_from_draft` function:
* Add logic to parse the specific JSON key.
* Call `add_items_to_file` targeting the `[TARGET_META_FILE]`.
* Add a print statement for logging (e.g., `print_section("PROCESSING FONTS")`).





## 🚀 Phase 3: Server Implementation (`api_server.py`)

1. **Check Existing Endpoint:**
* Scan `api_server.py`. Does an endpoint like `/add_[feature_name]` exist?
* If yes, skip to Phase 4.


2. **Implement Endpoint:**
* Define a Pydantic model (if specific parameters are needed).
* Create a POST route: `@app.post("/add_[feature_name]")`.
* **Logic inside endpoint:**
* Accept `draft_id` and feature-specific params (e.g., `font_size`, `duration`).
* Use `pycapcut` methods to add the resource to the `ScriptFile`.
* Save the script.


* **Error Handling:** Wrap in `try...except` block.



## 📄 Phase 4: Documentation Sync (`Curl.txt` / Notion Docs)

1. **Generate Documentation Block:**
* Create a Markdown/Text block following the existing project standard:
* **Heading:** `API: Add [Feature Name]`
* **Endpoint Info:** Method (POST) & URL.
* **cURL Request:** A complete, working example with JSON body.
* **Parameters:** Table/List of required and optional parameters.




2. **Append to Files:**
* Append this block to `Curl.txt` (or the main API documentation file).
* Ensure it is placed in the relevant section (e.g., Media, Text, Effects).



## ✅ Definition of Done

* [ ] The sync script now extracts the new resource type from the draft.
* [ ] The metadata file is populated with real IDs from the user's machine.
* [ ] The `api_server.py` runs without errors and exposes the new endpoint.
* [ ] The Documentation file contains the new cURL command for testing.

---

### 📝 Example Execution for User Prompt:

> *"Implement `material_animations` (loop) -> `text_loop.py`"*

**Agent Actions:**

1. Read `draft_content.json`.
2. Look for `materials.material_animations` where `type == "loop"`.
3. If found:
* Update `sync_script.py` to write to `metadata/text_loop.py`.
* Update `api_server.py` to add `@app.post("/add_text_loop_animation")`.
* Update `Curl.txt` with the new cURL command.



---