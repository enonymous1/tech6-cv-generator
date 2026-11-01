"use strict";

/* tech6-cv-generator — JSON authoring form (static site, no backend).
 *
 * Everything here runs in the visitor's browser. Nothing is uploaded:
 * "Load sample" fetches the fictional sample JSON from this same site,
 * "Download JSON" builds the file locally with a Blob, and DOCX
 * generation itself still happens with the Python CLI (see the
 * "Generate the DOCX" section on the page). The form therefore never
 * duplicates the DOCX layout — it only authors the JSON the CLI
 * already accepts, in the same shape as examples/sample_data.json
 * (education as free text, languages as a comma-separated string,
 * employment and adequacy as lists of objects).
 */

function isPlaceholder(value) {
  // Mirrors the builder's rule in form_builder.is_placeholder: empty,
  // brace-wrapped, or starting with "insert" counts as missing.
  if (typeof value !== "string" || !value.trim()) return true;
  const s = value.trim();
  return s.startsWith("{") || s.endsWith("}") || s.toLowerCase().startsWith("insert");
}

function parseLines(text) {
  // One item per line, blank lines dropped. Used for publications.
  return String(text || "")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
}

function employmentContactHasDetails(contact) {
  // Mirrors the builder's reference check: a reference counts as
  // usable when it carries an email or a digit (a phone number).
  // "Available on request" with no details is flagged, not accepted.
  if (!contact || !String(contact).trim()) return false;
  const lower = String(contact).toLowerCase();
  const hasEmail = contact.includes("@");
  const hasPhone = /\d/.test(contact);
  if (!hasEmail && !hasPhone) return false;
  if (/(on request|available on request|available upon request)/.test(lower)) {
    // "On request" plus real details is still usable; on its own it is not.
    return hasEmail || hasPhone;
  }
  return true;
}

function validateExpert(data) {
  // Returns a list of human-readable gaps, in the same spirit as the
  // builder's yellow highlighting. An empty list means "no gaps found",
  // not "submittable" — the CLI is the final judge.
  const issues = [];
  if (isPlaceholder(data.position_title)) issues.push("Position title is missing or a placeholder.");
  if (isPlaceholder(data.name)) issues.push("Name is missing or a placeholder.");
  if (isPlaceholder(data.dob)) issues.push("Date of birth is missing or a placeholder.");
  if (isPlaceholder(data.citizenship)) issues.push("Citizenship/residence is missing or a placeholder.");
  const contact = data.contact || {};
  if (!contact.email && !contact.phone) {
    issues.push("Contact email and phone are both missing.");
  }
  (data.employment || []).forEach((job, i) => {
    const label = job.organization || job.title || `employment entry ${i + 1}`;
    if (!employmentContactHasDetails(job.contact)) {
      issues.push(`Employment reference for "${label}" is missing or has no contact details.`);
    }
  });
  return issues;
}

function buildExpertJson(state) {
  // Build the CLI-ready object from a plain state object (no DOM here,
  // so this function is unit-testable from Node). Empty optional
  // sections are omitted rather than emitted as empty strings/lists,
  // except contact, which the builder expects as an object.
  const data = {
    position_title: state.positionTitle || "",
    name: state.name || "",
    dob: state.dob || "",
    citizenship: state.citizenship || "",
    education: state.education || "",
    employment: (state.employment || []).map((job) => ({
      period: job.period || "",
      title: job.title || "",
      organization: job.organization || "",
      contact: job.contact || "",
      country: job.country || "",
      summary: job.summary || "",
    })),
    memberships: state.memberships || "",
    languages: state.languages || "",
    contact: { email: state.email || "", phone: state.phone || "" },
  };
  const publications = parseLines(state.publications);
  if (publications.length) data.publications = publications;
  const adequacy = (state.adequacy || [])
    .filter((row) => (row.task || "").trim() || (row.reference || "").trim())
    .map((row) => ({ task: row.task || "", reference: row.reference || "" }));
  if (adequacy.length) data.adequacy_for_assignment = adequacy;
  if ((state.certificationText || "").trim()) {
    data.certification_text = state.certificationText;
  }
  if ((state.authorizedRepresentative || "").trim()) {
    data.authorized_representative = state.authorizedRepresentative;
  }
  return data;
}

function downloadFilename(name) {
  // Same idea as the builder's safe stem: spaces to underscores, only
  // safe characters kept, so the filename cannot escape a folder.
  const stem = String(name || "")
    .trim()
    .replace(/\s+/g, "_")
    .replace(/[^A-Za-z0-9_.\-]/g, "_")
    .replace(/^[._]+/, "");
  return (stem || "expert") + ".json";
}

function expertFromJson(raw) {
  // Normalize a loaded JSON object into form state. Education may be
  // a string (sample data) or a list of objects (mapped data); the
  // list form is flattened to readable lines for the free-text field.
  // Languages may be a string or a list; both become the input string.
  let education = raw.education || "";
  if (Array.isArray(education)) {
    education = education
      .map((e) => {
        if (typeof e === "string") return e;
        const years = [e.start_year, e.end_year].filter(Boolean).join("-");
        return `${e.institution || ""} - ${e.degree || ""}${years ? ` (${years})` : ""}${e.notes ? `: ${e.notes}` : ""}`.trim();
      })
      .join("\n");
  }
  let languages = raw.languages || "";
  if (Array.isArray(languages)) languages = languages.join(", ");
  let adequacy = raw.adequacy_for_assignment || [];
  if (!adequacy.length && typeof raw.tasks === "string" && raw.tasks.trim()) {
    // Legacy "tasks" string: keep it as a single adequacy row so the
    // information is not silently dropped on load.
    adequacy = [{ task: raw.tasks, reference: "" }];
  }
  const publications = Array.isArray(raw.publications)
    ? raw.publications.join("\n")
    : raw.publications || "";
  return {
    positionTitle: raw.position_title || "",
    name: raw.name || "",
    dob: raw.dob || "",
    citizenship: raw.citizenship || "",
    education,
    employment: Array.isArray(raw.employment) ? raw.employment : [],
    memberships: raw.memberships || "",
    publications,
    languages,
    adequacy,
    email: (raw.contact && raw.contact.email) || "",
    phone: (raw.contact && raw.contact.phone) || "",
    certificationText: raw.certification_text || "",
    authorizedRepresentative: raw.authorized_representative || "",
  };
}

/* ---- DOM wiring (browser only; skipped when loaded from Node) ---- */

if (typeof document !== "undefined") {
  document.addEventListener("DOMContentLoaded", () => {
    const $ = (id) => document.getElementById(id);
    const preview = $("json-preview");
    const validation = $("validation");
    const status = $("form-status");

    function rowHtml(kind, job) {
      // One dynamic row for employment or adequacy. Values are set via
      // the input elements after insertion, never via innerHTML with
      // user data, so loaded JSON cannot inject markup.
      const wrap = document.createElement("div");
      wrap.className = "dyn-row";
      const fields =
        kind === "employment"
          ? [
              ["period", "Period (e.g. Jan 2020 - Present)"],
              ["organization", "Employing organization"],
              ["title", "Title / position"],
              ["country", "Country"],
              ["contact", "Reference contact (email / phone)"],
              ["summary", "Summary of relevant activities"],
            ]
          : [
              ["task", "Detailed task assigned"],
              ["reference", "Reference to prior work"],
            ];
      fields.forEach(([key, label]) => {
        const lab = document.createElement("label");
        lab.textContent = label;
        const input = document.createElement("input");
        input.type = "text";
        input.dataset.field = key;
        input.value = (job && job[key]) || "";
        input.addEventListener("input", refresh);
        lab.appendChild(input);
        wrap.appendChild(lab);
      });
      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "secondary remove-row";
      remove.textContent = "Remove";
      remove.addEventListener("click", () => {
        wrap.remove();
        refresh();
      });
      wrap.appendChild(remove);
      return wrap;
    }

    function collectRows(containerId) {
      const rows = [];
      document.querySelectorAll(`#${containerId} .dyn-row`).forEach((row) => {
        const obj = {};
        row.querySelectorAll("input[data-field]").forEach((input) => {
          obj[input.dataset.field] = input.value;
        });
        rows.push(obj);
      });
      return rows;
    }

    function collectState() {
      return {
        positionTitle: $("position_title").value,
        name: $("name").value,
        dob: $("dob").value,
        citizenship: $("citizenship").value,
        education: $("education").value,
        employment: collectRows("employment-rows"),
        memberships: $("memberships").value,
        publications: $("publications").value,
        languages: $("languages").value,
        adequacy: collectRows("adequacy-rows"),
        email: $("email").value,
        phone: $("phone").value,
        certificationText: $("certification_text").value,
        authorizedRepresentative: $("authorized_representative").value,
      };
    }

    function setRows(containerId, kind, items) {
      const container = $(containerId);
      container.innerHTML = "";
      (items && items.length ? items : [{}]).forEach((item) => {
        container.appendChild(rowHtml(kind, item));
      });
    }

    function fillForm(state) {
      $("position_title").value = state.positionTitle;
      $("name").value = state.name;
      $("dob").value = state.dob;
      $("citizenship").value = state.citizenship;
      $("education").value = state.education;
      $("memberships").value = state.memberships;
      $("publications").value = state.publications;
      $("languages").value = state.languages;
      $("certification_text").value = state.certificationText;
      $("authorized_representative").value = state.authorizedRepresentative;
      $("email").value = state.email;
      $("phone").value = state.phone;
      setRows("employment-rows", "employment", state.employment);
      setRows("adequacy-rows", "adequacy", state.adequacy);
      refresh();
    }

    function refresh() {
      const data = buildExpertJson(collectState());
      preview.textContent = JSON.stringify(data, null, 2);
      const issues = validateExpert(data);
      if (!issues.length) {
        validation.innerHTML = "";
        const ok = document.createElement("p");
        ok.className = "ok";
        ok.textContent = "No gaps found in the fields above.";
        validation.appendChild(ok);
      } else {
        validation.innerHTML = "";
        const list = document.createElement("ul");
        issues.forEach((issue) => {
          const item = document.createElement("li");
          item.textContent = issue;
          list.appendChild(item);
        });
        validation.appendChild(list);
      }
    }

    document.querySelectorAll("#author-form input, #author-form textarea").forEach((el) => {
      el.addEventListener("input", refresh);
    });
    $("add-employment").addEventListener("click", () => {
      $("employment-rows").appendChild(rowHtml("employment", {}));
      refresh();
    });
    $("add-adequacy").addEventListener("click", () => {
      $("adequacy-rows").appendChild(rowHtml("adequacy", {}));
      refresh();
    });

    $("load-sample").addEventListener("click", async () => {
      status.textContent = "";
      try {
        const res = await fetch("sample_data.json");
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        fillForm(expertFromJson(await res.json()));
        status.textContent = "Loaded the fictional sample (Jane Q. Expert).";
      } catch (err) {
        status.textContent = `Could not load the sample: ${err.message}. On a local copy, serve the site folder over HTTP.`;
      }
    });

    $("load-file").addEventListener("change", async (event) => {
      status.textContent = "";
      const file = event.target.files[0];
      if (!file) return;
      try {
        fillForm(expertFromJson(JSON.parse(await file.text())));
        status.textContent = `Loaded ${file.name}.`;
      } catch (err) {
        status.textContent = `Could not parse ${file.name}: ${err.message}`;
      }
      event.target.value = "";
    });

    $("download-json").addEventListener("click", () => {
      const data = buildExpertJson(collectState());
      const blob = new Blob([JSON.stringify(data, null, 2) + "\n"], { type: "application/json" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = downloadFilename(data.name);
      a.click();
      URL.revokeObjectURL(a.href);
      status.textContent = `Downloaded ${a.download}. Generate the DOCX with the CLI command below.`;
    });

    $("copy-command").addEventListener("click", async () => {
      const data = buildExpertJson(collectState());
      const cmd = `tech6-cv-generator generate ${downloadFilename(data.name)}`;
      try {
        await navigator.clipboard.writeText(cmd);
        status.textContent = `Copied: ${cmd}`;
      } catch {
        status.textContent = cmd;
      }
    });

    $("clear-form").addEventListener("click", () => {
      fillForm(expertFromJson({}));
      status.textContent = "Form cleared.";
    });

    setRows("employment-rows", "employment", [{}]);
    setRows("adequacy-rows", "adequacy", []);
    refresh();
  });
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    isPlaceholder,
    parseLines,
    employmentContactHasDetails,
    validateExpert,
    buildExpertJson,
    downloadFilename,
    expertFromJson,
  };
}
if (typeof window !== "undefined") {
  window.Tech6Form = {
    isPlaceholder,
    parseLines,
    employmentContactHasDetails,
    validateExpert,
    buildExpertJson,
    downloadFilename,
    expertFromJson,
  };
}
