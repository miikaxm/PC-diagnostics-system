"use strict";

// Haetaan elementit
const startButton = document.getElementById("start-button");
const selectAllButton = document.getElementById("select-all");
const clearAllButton = document.getElementById("clear-all");
const message = document.getElementById("message");
const statusText = document.getElementById("status");
const currentTestText = document.getElementById("current-test");
const progressContainer = document.getElementById("progress-container");
const progressBar = document.getElementById("progress-bar");
const progressText = document.getElementById("progress-text");
const testProgress = document.getElementById("test-progress");
const resultsContainer = document.getElementById("results");
const savedFileText = document.getElementById("saved-file");

const smartCheckbox = document.querySelector(
  '.test-checkbox[value="smart"]'
)

const smartOptions = document.getElementById("smart-options");
const smartDevice = document.getElementById("smart-device");
const smartDeviceMessage = document.getElementById("smart-device-message");

const historyList = document.getElementById("history-list");
const historyMessage = document.getElementById("history-message");
const historyDetails = document.getElementById("history-details");
const historyDetailsContent = document.getElementById("history-details-content");
const refreshHistoryButton = document.getElementById("refresh-history");

// Palauttaa testien valintaruudut
function getCheckBoxes() {
  return Array.from(
    document.querySelectorAll(".test-checkbox")
  );
}

// Palauttaa testin käyttöliittymässä näkyvän nimen
function getTestName(testId) {
  const checkbox = getCheckBoxes().find(
    box => box.value === testId
  );

  return checkbox ? checkbox.dataset.name : testId;
}

// Valitaan kaikki testit
function selectAll() {
  getCheckBoxes().forEach(box => {
    box.checked = true;
  });

  updateSmartVisibility()
}

// Tyhjennetään testien valinnat
function clearAll() {
  getCheckBoxes().forEach(box => {
    box.checked = false;
  });

  updateSmartVisibility()
}

// Haetaan valitut testit
function getSelectedTests() {
  return getCheckBoxes()
    .filter(box => box.checked)
    .map(box => box.value);
}

// Estetään valintojen muuttaminen kun testejä ajetaan
function setRunning(running) {
  startButton.disabled = running;
  selectAllButton.disabled = running;
  clearAllButton.disabled = running;

  getCheckBoxes().forEach(box => {
    box.disabled = running;
  });
}

// Ajankohdat selkeästi suomalaiseen muotoon
function formatHistoryDate(value) {
  if (!value) {
    return "Tuntematon ajankohta";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString("fi-FI");
}

function createHistoryText(tagName, text, className = "") {
  const element = document.createElement(tagName);
  element.textContent = String(text ?? "");

  if (className) {
    element.className = className;
  }

  return element;
}


function createHistoryDetail(label, value) {
  const row = document.createElement("div");
  row.className = "history-detail-row";

  row.appendChild(
    createHistoryText("strong", label)
  );

  row.appendChild(
    createHistoryText("span", value ?? "Ei tietoa")
  );

  return row;
}

// Ladataan aiemmat testitulokset käyttöliittymään näkyviin
async function loadHistory() {
  historyMessage.textContent = "Haetaan testihistoriaa...";
  historyList.replaceChildren();

  try {
    // Haetaan testihistoria
    const response = await fetch("/api/history");
    const data = await response.json();

    // Jos hakeminen ei onnistu ilmoitetaan siitä
    if (!response.ok) {
      throw new Error(
        data.error || "Testihistorian hakeminen epäonnistui"
      );
    }

    const runs = data.runs || [];

    // Jos testikertoja ei vielä ole niin ilmoitetaan siitä
    if (runs.length === 0) {
      historyMessage.textContent =
        "Aikaisempia diagnostiikkakertoja ei vielä ole.";
      historyDetails.hidden = true;
      return;
    }

    // asetetaan historyMessage elementin tekstiksti aiempien testikertojen määrä
    historyMessage.textContent =
      `Tallennettuja testikertoja: ${runs.length}`;

    // Käydään kaikki testikerrat läpi ja tehdään niille omat html elementit
    for (const run of runs) {
      const item = document.createElement("div");
      item.className = "history-item";

      const info = document.createElement("div");
      info.className = "history-item-info";

      // Lisätään tietokone nimi, aloitusaika ja testien määrä
      info.appendChild(
        createHistoryText(
          "strong",
          run.hostname || "Tuntematon tietokone"
        )
      );

      info.appendChild(
        createHistoryText(
          "span",
          formatHistoryDate(run.started_at)
        )
      );

      info.appendChild(
        createHistoryText(
          "span",
          `Testejä: ${run.test_count}`
        )
      );

      const actions = document.createElement("div");
      actions.className = "history-item-actions";

      const status = createHistoryText(
        "span",
        run.status,
        "history-status"
      );

      // Asetetaan testikerran status esim. PASS
      status.dataset.status = run.status;

      // Näpppi testikerran tarkemmille tiedoille
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = "Näytä tulokset";

      // Ladataan testikerran tarkemmat tiedot kun nappia painetaan
      button.addEventListener("click", () => {
        loadHistoryDetails(run.run_id);
      });

      actions.appendChild(status);
      actions.appendChild(button);

      item.appendChild(info);
      item.appendChild(actions);

      historyList.appendChild(item);
    }

  } catch (error) {
    historyMessage.textContent = error.message;
  }
}

// Ladataan testikerran tarkemmat tiedot
async function loadHistoryDetails(runId) {
  // Asetetaan tarkemmat tiedot näkyväksi
  historyDetails.hidden = false;
  historyDetailsContent.replaceChildren();

  historyDetailsContent.appendChild(
    createHistoryText("p", "Haetaan testikerran tietoja...")
  );

  try {
    // Haetaan tarkemmat tiedot
    const response = await fetch(
      `/api/history/${encodeURIComponent(runId)}`
    );

    const run = await response.json();

    // Jos haku ei onnistu ilmoitetaan siitä
    if (!response.ok) {
      throw new Error(
        run.error || "Testikerran hakeminen epäonnistui"
      );
    }

    historyDetailsContent.replaceChildren();

    // Asetetaan tietokoneen malli, aloitusaika, valmistumisaika sekä yhteenveto statuksesta
    historyDetailsContent.appendChild(
      createHistoryDetail(
        "Tietokone",
        run.hostname || "Tuntematon"
      )
    );

    historyDetailsContent.appendChild(
      createHistoryDetail(
        "Aloitusaika",
        formatHistoryDate(run.timestamp)
      )
    );

    historyDetailsContent.appendChild(
      createHistoryDetail(
        "Valmistumisaika",
        formatHistoryDate(run.finished_at)
      )
    );

    historyDetailsContent.appendChild(
      createHistoryDetail(
        "Yhteenveto",
        run.status
      )
    );

    // Käydään jokainen tulos läpi ja luodaan niistä html elementit
    for (const result of run.results) {
      const card = document.createElement("div");
      card.className = "history-result-card";

      // Testin nimi
      card.appendChild(
        createHistoryText(
          "h4",
          result.test_name
        )
      );

      // Testin status
      const status = createHistoryText(
        "span",
        result.status,
        "history-status"
      );

      status.dataset.status = result.status;
      card.appendChild(status);

      // Testin tuloksen viesti
      card.appendChild(
        createHistoryText(
          "p",
          result.message
        )
      );

      const details = document.createElement("details");
      const summary = document.createElement("summary");
      summary.textContent = "Näytä mittaustiedot";

      // Tarkemmat yksittäisen testin tiedot
      const pre = createHistoryText(
        "pre",
        JSON.stringify(result.details, null, 2)
      );

      details.appendChild(summary);
      details.appendChild(pre);

      card.appendChild(details);
      historyDetailsContent.appendChild(card);
    }

  } catch (error) {
    historyDetailsContent.replaceChildren();

    historyDetailsContent.appendChild(
      createHistoryText("p", error.message)
    );
  }
}

// Refresh nappi päivittää testikertojen historia
refreshHistoryButton.addEventListener(
  "click",
  loadHistory
);

loadHistory();

// Näytetään levyvalitsin vain smart-testin ollessa valittu
function updateSmartVisibility() {
  smartOptions.hidden = !smartCheckbox.checked;
}

// Haetaan valittavissa olevat levyt
async function loadSmartDisks() {
  smartDevice.disabled = true
  smartDevice.replaceChildren()

  const placeholder = document.createElement("option")
  placeholder.value = ""
  placeholder.textContent = "Haetaan tallennuslevyjä..."

  smartDevice.appendChild(placeholder)

  try {
    const response = await fetch("/api/disks")
    const data = await response.json()

    if (!response.ok) {
      throw new Error(
        data.error || "Tallennuslevyjä ei saatu haettua"
      );
    }

    smartDevice.replaceChildren();

    const firstOption = document.createElement("option")
    firstOption.value = ""
    firstOption.textContent = "Valitse levy"

    smartDevice.appendChild(firstOption)

    for (const disk of data.disks) {
      const option = document.createElement("option")

      option.value = disk.id;

      const size = disk.size_gib != null
        ? `${disk.size_gib} GiB`
        : "Tuntematon koko";
      
      option.textContent =
        `${disk.model} - ${size} - ${disk.interface}`;
      
      smartDevice.appendChild(option)
    }

    smartDevice.disabled = data.disks.length === 0;

    smartDeviceMessage.textContent = data.disks.length > 0
      ? "Debianin käynnistyslevy on rajattu pois."
      : "Valittavia tallennuslevyjä ei löytynyt."
    
  } catch (error) {
    smartDeviceMessage.textContent = error.message;
  }
}

// Käynnistetään valitut testit Flaskin kautta
async function startTests() {
  const selected = getSelectedTests();

  if (selected.length === 0) {
    message.textContent = "Valitse vähintään yksi testi.";
    return;
  }

  // smart-testi vaatii valitun levyn
  if (selected.includes("smart") && !smartDevice.value) {
    message.textContent = "Valitse ensin tarkistettava levy.";
    return;
  }

  setRunning(true);
  message.textContent = "";

  try {
    const response = await fetch("/api/start", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        selected_tests: selected,
        smart_device: selected.includes("smart")
          ? smartDevice.value
          : null
      })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(
        data.error || "Testien käynnistys epäonnistui."
      );
    }

    message.textContent = data.message;

  } catch (error) {
    message.textContent = error.message;
  }

  await updateStatus();
}

// Näytetään yksittäisten testien eteneminen

 // Näytetään yksittäisten testien eteneminen
function renderTestProgress(data) {
  testProgress.replaceChildren();

  // Käydään valitut testit läpi suoritusjärjestyksessä
  data.selected_tests.forEach((testId, index) => {
    const row = document.createElement("div");
    row.className = "progress-item";

    const name = document.createElement("span");
    name.textContent = getTestName(testId);

    const state = document.createElement("span");
    state.className = "progress-status";

    // Testimoottori palauttaa tulokset samassa järjestyksessä
    // kuin testit suoritetaan
    if (index < data.completed) {
      const result = data.results[index];

      state.textContent = result
        ? result.status
        : "Valmis";

    } else if (
      data.status === "running"
      && data.current_test === testId
    ) {
      state.textContent = "Käynnissä";

    } else if (data.status === "error") {
      state.textContent = "Ei suoritettu";

    } else {
      state.textContent = "Odottaa";
    }

    row.append(name, state);
    testProgress.appendChild(row);
  });
}

// Näytetään valmiiden testien tulokset
function renderResults(results) {
  resultsContainer.replaceChildren();

  if (results.length === 0) {
    resultsContainer.textContent = "Ei vielä tuloksia.";
    return;
  }

  for (const result of results) {
    const item = document.createElement("div");
    item.className = "result";

    if (["PASS", "WARNING", "FAIL", "UNKNOWN"]
      .includes(result.status)) {
      item.classList.add(result.status);
    }

    const title = document.createElement("strong");
    title.textContent =
      `${result.test_name}: ${result.status}`;

    const description = document.createElement("p");
    description.textContent = result.message || "";

    item.append(title, description);
    resultsContainer.appendChild(item);
  }
}

// Haetaan testien tila Flask-palvelimelta
async function updateStatus() {
  try {
    const response = await fetch("/api/status");

    if (!response.ok) {
      throw new Error("Tilatietoja ei saatu.");
    }

    const data = await response.json();

    // Päivitetään valmistuneiden testien prosenttiosuus
    const percentage = data.total > 0
      ? Math.round((data.completed / data.total) * 100)
      : 0;

    progressBar.style.width = percentage + "%";

    progressContainer.setAttribute(
      "aria-valuenow",
      String(percentage)
    );

    progressText.textContent =
      `${data.completed} / ${data.total} testiä valmis `
      + `(${percentage} %)`;

    // Päivitetään koko testiajon tila
    if (data.status === "running") {
      statusText.textContent = "Testejä suoritetaan...";

      currentTestText.textContent = data.current_test
        ? "Käynnissä: " + getTestName(data.current_test)
        : "Valmistellaan testejä...";

    } else if (data.status === "finished") {
      statusText.textContent =
        "Kaikki valitut testit on suoritettu.";

      currentTestText.textContent = "";

    } else if (data.status === "error") {
      statusText.textContent =
        "Testiajon suoritus epäonnistui.";

      currentTestText.textContent = data.error || "";

    } else {
      statusText.textContent =
        "Ei käynnissä olevia testejä.";

      currentTestText.textContent = "";
    }

    // Näytetään tulostiedoston sijainti
    savedFileText.textContent = data.saved_file
      ? "Tulokset tallennettu: " + data.saved_file
      : "";

    // Estetään painikkeiden käyttö testiajon aikana
    setRunning(data.status === "running");

    // Päivitetään testien eteneminen ja tulokset
    renderTestProgress(data);
    renderResults(data.results);

  } catch (error) {
    statusText.textContent =
      "Yhteyttä Flask-palvelimeen ei saatu.";

    currentTestText.textContent = "";
    message.textContent = error.message;

    // Painikkeet palautetaan käyttöön yhteysvirheessä.
    // Flask tarkistaa erikseen, ettei päällekkäisiä ajoja aloiteta.
    setRunning(false);
  }
}

// Yhdistetään painikkeet niiden toimintoihin
selectAllButton.addEventListener("click", selectAll);
clearAllButton.addEventListener("click", clearAll);
startButton.addEventListener("click", startTests);
smartCheckbox.addEventListener(
  "change",
  updateSmartVisibility
);

// Haetaan tietokoneen laitteistotiedot

async function loadHardwareInfo() {
  const hardwareInfo = document.getElementById("hardware-info");

  try {
    const response = await fetch("/api/hardware");
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Laitteistotietoja ei saatu.");
    }

    // Yhdistetään tietokoneen valmistaja ja malli
    const computer = [
      data.computer?.manufacturer,
      data.computer?.model
    ].filter(Boolean).join(" ");

    // Yhdistetään emolevyn valmistaja ja malli
    const motherboard = [
      data.motherboard?.manufacturer,
      data.motherboard?.model
    ].filter(Boolean).join(" ");

    // Haetaan näytönohjaimet model-kentästä
    const graphics = (data.graphics_cards || [])
      .map(card => card.model)
      .filter(Boolean)
      .join(", ");

    // Haetaan tallennuslevyjen nimet ja kapasiteetit
    const storage = (data.storage_devices || [])
      .map(disk => {
        const name = disk.model || disk.name || "Tuntematon levy";

        const size = disk.size_gb != null
          ? `${disk.size_gb} GiB`
          : "Koko ei saatavilla";

        return `${name} (${size})`;
      })
      .join(", ");

    // Muodostetaan käyttöliittymässä näytettävät tiedot
    const hardware = [
      ["Tietokone: ", computer],
      ["Prosessori: ", data.cpu?.model],
      ["RAM-muisti: ", data.memory?.total_gb != null
        ? `${data.memory.total_gb} GiB`
        : null],
      ["Emolevy: ", motherboard],
      ["BIOS-versio: ", data.bios?.version],
      ["Näytönohjain: ", graphics],
      ["Tallennuslevyt: ", storage]
    ];

    // Tyhjennetään vanhat tiedot
    hardwareInfo.replaceChildren();

    // Lisätään laitteistotiedot sivulle
    for (const [name, value] of hardware) {
      const row = document.createElement("div");
      row.className = "hardware-row";

      const label = document.createElement("strong");
      label.textContent = name;

      const information = document.createElement("span");
      information.textContent = value || "Ei saatavilla";

      row.append(label, information);
      hardwareInfo.appendChild(row);
    }

  } catch (error) {
    hardwareInfo.textContent = error.message;
  }
}

// haetaan tiedot
loadHardwareInfo()
updateSmartVisibility();
loadSmartDisks();

// Päivitetään testien tilanne kahden sekunnin välein
setInterval(updateStatus, 2000);

// Haetaan tilanne heti käyttöliittymän avautuessa
updateStatus();