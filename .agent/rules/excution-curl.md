---
trigger: manual
---

Đây là file hướng dẫn **Markdown (.md)** dành cho Agent (Vibe Code) để thực hiện quy trình phát triển tính năng mới dựa trên yêu cầu cURL, đảm bảo tính nhất quán giữa Code và Tài liệu.

Bạn lưu file này với tên: **`AGENT_TASK_IMPLEMENT_ENDPOINT.md`**

---

# 🤖 AGENT TASK: Implement & Sync Endpoint

**Objective:** This protocol directs the agent to analyze the current codebase, implement a requested API endpoint in `api_server.py` based on a provided cURL structure, and ensure the documentation in `Curl.txt` is perfectly synchronized.

**Context Sources:**

1. `api_server.py` (Main logic)
2. `Curl.txt` (Documentation source of truth)
3. `Vinh_add_efffect_to_file.py` (Resource sync logic & data structure understanding)
4. `pycapcut/metadata/` folder (To understand available Enums/Classes like `EffectMeta`, `FontType`)

**Trigger Command:** `implement endpoint [CURL_COMMAND_OR_DESCRIPTION]`

---

## 🔍 Phase 1: Context Analysis

1. **Read Context Files:**
* Scan `api_server.py` to understand the import structure (`import pycapcut as cc`) and Pydantic models.
* Scan `Vinh_add_efffect_to_file.py` to understand how resource IDs are mapped (e.g., `EffectMeta`, `TransitionMeta`).
* Scan `pycapcut/metadata/*.py` to check if the requested feature uses specific Enum types or raw IDs.


2. **Analyze Request:**
* Parse the input cURL command or description.
* Identify the target endpoint route (e.g., `/add_glitch`).
* Identify required parameters (Body payload).


3. **Existence Check:**
* Search `api_server.py` for `@app.post("TARGET_ROUTE")`.
* **IF Exists:** Stop implementation, proceed to Phase 3 (Doc Sync check).
* **IF Missing:** Proceed to Phase 2.



---

## 🛠️ Phase 2: Server Implementation (`api_server.py`)

1. **Define Data Model:**
* If the endpoint requires complex JSON body, define a `class [Feature]Request(BaseModel)` at the top of `api_server.py`.
* *Style Guide:* Follow existing models like `VideoRequest` or `EffectRequest`.


2. **Implement Route Logic:**
* Create the function: `def add_[feature]_endpoint(req: [Model])`.
* **Draft Loading:** Use `cc.DraftFolder` and `script.load()` or reuse active session logic.
* **Action:** Call the appropriate `pycapcut` method (e.g., `script.add_segment`, `script.add_effect`).
* *Tip:* If the feature requires a Resource ID, look at how `Vinh_add_efffect_to_file.py` extracts them to understand where to look in `metadata`.


* **Save:** Call `script.save()`.
* **Response:** Return a standard JSON response: `{"success": true, "draft_id": ...}`.


3. **Error Handling:**
* Wrap logic in `try...except Exception as e`.
* Raise `HTTPException(status_code=500, detail=str(e))`.



---

## 📄 Phase 3: Documentation Sync (`Curl.txt`)

1. **Check `Curl.txt`:**
* Search if the endpoint is already documented.
* If yes, update parameters if they changed.
* If no, append a new section.


2. **Generate Documentation Block:**
* Follow this strict template (consistent with existing `Curl.txt`):


```text
# ====================================================================================================
# [EMOJI] API: [Feature Name] (`[ROUTE]`)
# ====================================================================================================
# [Short description of what it does]

# 🔌 Endpoint Info
# | Method | URL                            |
# | POST   | http://localhost:8000[ROUTE]   |

# 💻 cURL Request (Full Options)
[PASTE THE CURL COMMAND HERE]

# 📋 Chi Tiết Tham Số
# 🔴 BẮT BUỘC (Required)
# | Tham số | Kiểu | Mô tả |
# | ...     | ...  | ...   |

# 🟡 OPTIONAL
# | Tham số | Default | Mô tả |
# | ...     | ...     | ...   |

```


3. **Insert Location:**
* Place the new block in the logical section (e.g., put Video APIs with other Video APIs). Do not just append to the very end if a better category exists.



---

## ✅ Execution Checklist

* [ ] **Analysis:** Confirmed endpoint does not exist or needs update.
* [ ] **Code:** `api_server.py` updated with valid Python code.
* [ ] **Validation:** The Python code uses correct `pycapcut` syntax (checked against `Vinh_add_efffect_to_file.py` logic).
* [ ] **Docs:** `Curl.txt` updated with a working cURL example.

---

### 📝 Example Usage

**User Prompt:**

> "Implement endpoint `/add_sticker` based on this curl: `curl -X POST ... -d '{"sticker_id": "123", "x": 0, "y": 0}'`"

**Agent Actions:**

1. Reads `api_server.py`, sees `/add_sticker` is missing.
2. Reads `metadata/sticker_meta.py` (inferred from context) to see how sticker IDs are stored.
3. Adds `@app.post("/add_sticker")` to `api_server.py`.
4. Appends the documented cURL to `Curl.txt` under the "Media" or "Sticker" section.