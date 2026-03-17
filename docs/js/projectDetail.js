function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

function getQueryParam(name) {
    return new URLSearchParams(window.location.search).get(name);
}

function renderOptionalLink(url) {
    if (!url) {
        return "";
    }
    const safeUrl = escapeHtml(url);
    return `<a href="${safeUrl}" target="_blank">${safeUrl}</a>`;
}

function renderListLines(items) {
    return items
        .filter((item) => item)
        .map((item) => `${item} <br>`)
        .join("");
}

function renderNotes(notes) {
    return notes
        .filter((note) => note)
        .map((note) => `${escapeHtml(note)} <br>`)
        .join("");
}

function renderGovChanges(changes) {
    return changes
        .slice()
        .reverse()
        .map((change) => {
            const lines = change.li
                .map((field) => {
                    return `${escapeHtml(field.name)}: ${escapeHtml(field.from)} -> ${escapeHtml(field.to)} ${field.extra || ""}<br>`;
                })
                .join("");
            return `<b>${escapeHtml(change.month)}</b><br>${lines}<br>`;
        })
        .join("");
}

function renderUsGovSection(project) {
    const blocks = Object.values(project.gov_history).map((gen) => {
        const multipleProjects = project.gov.has_multiple_projects
            ? `<span class="badge bg-info">This project has ${Object.values(project.gov_history).length} generator ids under the same plant id</span><br>`
            : "";

        return `${multipleProjects}
Info from the <code>${escapeHtml(gen.current_month)}</code> report (Project first appeared in the <code>${escapeHtml(gen.first_month)}</code> report):<br>
<br>
<dt>Plant Name / State</dt>
<dl>${escapeHtml(gen.current["plant name"])} / ${escapeHtml(gen.current["plant state"])}</dl>
<dt>go live / power</dt>
<dl>${escapeHtml(gen.current["date"])} / ${escapeHtml(gen.current["mw"])}MW</dl>
<dt>status / status verbose</dt>
<dl>${escapeHtml(gen.current["status"])} / ${escapeHtml(gen.current["status_verbose"])}</dl>
<dt>Plant id / generator id</dt>
<dl>${escapeHtml(gen.current["plant id"])} / ${escapeHtml(gen.current["generator id"])}</dl>
<dt>Entity name / entity id</dt>
<dl>${escapeHtml(gen.current["entity name"])} / ${escapeHtml(gen.current["entity id"])}</dl>
<b>Changes:</b><br>
${renderGovChanges(gen.changes)}
<br><br>`;
    });

    return blocks.join("");
}

function renderUkDeGovSection(project) {
    return `Info from the <code>${escapeHtml(project.gov_history.current_month)}</code> report
(Project first appeared in the <code>${escapeHtml(project.gov_history.first_month)}</code> report):<br>
<br>
<dt>Plant Name / State</dt>
<dl>${escapeHtml(project.gov.name)} / ${escapeHtml(project.gov.state)}</dl>
<dt>Go live / estimated go live</dt>
<dl>${escapeHtml(project.gov.start_operation)} / ${escapeHtml(project.gov.start_estimated)}</dl>
<dt>MW</dt>
<dl>${escapeHtml(project.gov.power_mw)}</dl>
<dt>Status</dt>
<dl>${escapeHtml(project.gov.status)}</dl>
<b>Changes:</b><br>
${renderGovChanges(project.gov_history.changes)}`;
}

function renderGovSection(project) {
    if (!project.has_gov_data) {
        return "";
    }

    const govInfo = window.govDataInfoDict[project.country];
    let details = "";
    if (project.country === "usa") {
        details = renderUsGovSection(project);
    } else if (project.country === "uk" || project.country === "germany") {
        details = renderUkDeGovSection(project);
    }

    const disappeared = project.gov.month_disappeared
        ? `${escapeHtml(project.gov.month_disappeared)}<br>
This project disappeared in the <code>${escapeHtml(project.gov.month_disappeared)}</code> report. <br>
That's why the status was set to <span class="${escapeHtml(project.status_class)}">${escapeHtml(project.status)}</span><br>`
        : "";

    return `
<h3>${escapeHtml(govInfo.name_short)} data</h3>
The government data source for this battery is the ${escapeHtml(govInfo.name_long)}
<br>
<a href="${escapeHtml(govInfo.source_url)}">${escapeHtml(govInfo.source_url)}</a>
<br><br>
${details}
<br>
${disappeared}
`;
}

function renderProject(project) {
    const projectWebsite = renderOptionalLink(project.csv.project_website);
    const dataFlags = [
        project.has_user_data ? "👤 user data" : "",
        project.has_ai_data ? "🤖 ai data" : "",
    ].filter((item) => item).join(" / ");

    const maybeConstructionTime = project.construction_time_month
        ? `${escapeHtml(project.construction_time_month)} months -> ${escapeHtml(project.construction_speed_mwh_per_month)} MWh/m`
        : "";

    const maybeCancelled = project.status === "cancelled"
        ? `<tr><td>Month disappeared</td><td>${escapeHtml(project.month_disappeared)}</td></tr>`
        : "";

    const maybeEstimate = project.mwh_is_estimate ? "<br>📏 This is an estimate" : "";

    return `
<h3>${escapeHtml(project.name)} ${project.emojis_with_tooltips}</h3>

<dt>Status</dt>
<dl><span class="${escapeHtml(project.status_class)}">${escapeHtml(project.status)}</span></dl>

<dt>Country / State / Closest City</dt>
<dl>${project.flag} ${escapeHtml(project.country)} / ${escapeHtml(project.state)} / ${escapeHtml(project.csv.city)}</dl>

<dt>Dates</dt>
<div class="row">
    <div class="col-lg-4">
        <table class="table table-bordered">
            <tr><td>First heard</td><td>${escapeHtml(project.date_first_heard)}</td></tr>
            <tr><td>Construction start</td><td>${escapeHtml(project.start_construction)}</td></tr>
            <tr><td>Operation start</td><td>${escapeHtml(project.start_operation)}</td></tr>
            <tr><td>Estimated start</td><td>${escapeHtml(project.start_estimated)}</td></tr>
            ${maybeCancelled}
            <tr><td>Construction time</td><td>${maybeConstructionTime}</td></tr>
        </table>
    </div>
</div>

<dt>Capacity in MWh</dt>
<dl>${escapeHtml(project.mwh)}${maybeEstimate}</dl>

<dt>Maximum Power in MW</dt>
<dl>${escapeHtml(project.mw)}</dl>

<dt>Manufacturer</dt>
<dl>${escapeHtml(project.csv.manufacturer)}</dl>

<dt>Type / Number of Packs / Cells</dt>
<dl>${escapeHtml(project.csv.type)} / ${escapeHtml(project.csv.no_of_battery_units)} / ${escapeHtml(project.csv.cells)}</dl>

<dt>Customer / Owner / Developer</dt>
<dl>${escapeHtml(project.csv.customer)} / ${escapeHtml(project.owner)} / ${escapeHtml(project.csv.developer)}</dl>

<dt>Use case</dt>
<dl>${escapeHtml(project.csv.use_case)}</dl>

<dt>Link to google maps satellite view</dt>
<dl><a href="${escapeHtml(project.google_maps_link)}" target="_blank">${escapeHtml(project.google_maps_link)}</a></dl>

<dt>Coordinates</dt>
<dl>${escapeHtml(project.lat)}, ${escapeHtml(project.long)}<br>${escapeHtml(project.coords_help_str)}</dl>

<div class="row">
    <div class="col-lg-6">
        <div style="height: 300px;" id="mapid"></div>
    </div>
</div>

<dt>Notes</dt>
<dl>${renderNotes(project.notes_split)}</dl>

<dt>Project website</dt>
<dl>${projectWebsite}</dl>

<dt>Data flags</dt>
<dl>${dataFlags}</dl>

<dt>Sources</dt>
<dl>${renderListLines(project.links.map(renderOptionalLink))}</dl>

<dt>Internal / External id</dt>
<dl>${escapeHtml(project.internal_id)} / ${escapeHtml(project.external_id)}</dl>

${renderGovSection(project)}
`;
}

function renderState(message) {
    document.getElementById("project-detail-root").innerHTML = `<div class="alert alert-warning" role="alert">${escapeHtml(message)}</div>`;
}

async function initProjectDetailPage() {
    const projectId = getQueryParam("id");
    if (!projectId) {
        renderState("No project id was provided.");
        return;
    }

    let response;
    try {
        response = await fetch(window.projectDataUrl);
    } catch (error) {
        renderState("Failed to load project data.");
        return;
    }

    if (!response.ok) {
        renderState("Failed to load project data.");
        return;
    }

    const projectsById = await response.json();
    const project = projectsById[projectId];
    if (!project) {
        renderState(`Project ${projectId} was not found.`);
        return;
    }

    document.title = `${project.internal_id} ${project.name} (${project.mwh}MWh)`;
    document.getElementById("project-detail-root").innerHTML = renderProject(project);

    generateBatteryMap([project], "mapid", true);
    $(function () {
        $('[data-toggle="tooltip"]').tooltip();
    });
}

$(document).ready(function() {
    initProjectDetailPage();
});
