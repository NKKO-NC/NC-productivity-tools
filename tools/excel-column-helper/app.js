const excelColumnHelperTranslations = {
  "zh-TW": {
    pageTitle: "Excel 相對欄位對照",
    brand: "Excel 工具",
    backHome: "回到首頁",
    installPwa: "安裝 App",
    themeToggleAria: "切換主題",
    themeTitle: "主題",
    themeSunset: "預設橘",
    themeOcean: "海藍",
    themeMeadow: "草綠",
    themeRainbow: "彩虹",
    eyebrow: "Excel 小工具",
    title: "Excel 相對欄位對照",
    intro: "輸入起始與結束欄位，例如 <strong>W</strong> 到 <strong>Z</strong>，工具會回傳範圍內從 1 開始的相對序號。",
    startLabel: "起始欄位",
    endLabel: "結束欄位",
    startPlaceholder: "例如 W",
    endPlaceholder: "例如 Z",
    generate: "產生對照表",
    reset: "重設",
    footnote: "支援 A 到 XFD，結果會依你輸入的起始欄位從 1 開始計算。",
    errorFormat: "請輸入 1 到 3 個英文字母。",
    errorLimit: "Excel 欄位上限是 XFD。",
    errorOrder: "起始欄位不能大於結束欄位。"
  },
  en: {
    pageTitle: "Excel Relative Column Helper",
    brand: "Excel Tool",
    backHome: "Back Home",
    installPwa: "Install App",
    themeToggleAria: "Switch theme",
    themeTitle: "Theme",
    themeSunset: "Sunset",
    themeOcean: "Ocean",
    themeMeadow: "Meadow",
    themeRainbow: "Rainbow",
    eyebrow: "Excel Utility",
    title: "Excel Relative Column Helper",
    intro: "Enter a start and end column, such as <strong>W</strong> to <strong>Z</strong>, and the tool will return relative indexes starting from 1 within that range.",
    startLabel: "Start Column",
    endLabel: "End Column",
    startPlaceholder: "For example W",
    endPlaceholder: "For example Z",
    generate: "Generate Table",
    reset: "Reset",
    footnote: "Supports A to XFD, and always counts from 1 based on the start column you enter.",
    errorFormat: "Please enter 1 to 3 letters.",
    errorLimit: "The maximum Excel column is XFD.",
    errorOrder: "The start column cannot be after the end column."
  }
};

const THEME_STORAGE_KEY = "excel-column-helper-theme";
const THEMES = {
  sunset: { color: "#b96a1d" },
  ocean: { color: "#1f7ea8" },
  meadow: { color: "#4f8a3c" },
  rainbow: { color: "#d94b4b" }
};

const state = {
  currentLanguage: "zh-TW",
  lastRange: null,
  lastMessageKey: "",
  currentTheme: "sunset"
};

const startInput = document.getElementById("start");
const endInput = document.getElementById("end");
const messageNode = document.getElementById("message");
const resultNode = document.getElementById("result");
const generateButton = document.getElementById("generateButton");
const resetButton = document.getElementById("resetButton");
const themeSwitcher = document.getElementById("themeSwitcher");
const themeTrigger = document.getElementById("themeTrigger");
const themePanel = document.getElementById("themePanel");
const themeButtons = Array.from(document.querySelectorAll("[data-theme-option]"));
const themeColorMeta = document.querySelector('meta[name="theme-color"]');
const MAX_VALUE = lettersToNumber("xfd");
const MOBILE_BREAKPOINT = 520;
const TABLET_BREAKPOINT = 760;
const DESKTOP_BREAKPOINT = 1080;

function lettersToNumber(value) {
  return value
    .toLowerCase()
    .split("")
    .reduce(function (total, char) {
      return total * 26 + (char.charCodeAt(0) - 96);
    }, 0);
}

function numberToLetters(value) {
  let current = value;
  let output = "";

  while (current > 0) {
    current -= 1;
    output = String.fromCharCode((current % 26) + 97) + output;
    current = Math.floor(current / 26);
  }

  return output;
}

function getCopy(key) {
  return excelColumnHelperTranslations[state.currentLanguage][key];
}

function isValidLetters(value) {
  return /^[a-zA-Z]{1,3}$/.test(value);
}

function clearOutput() {
  state.lastMessageKey = "";
  messageNode.textContent = "";
  resultNode.innerHTML = "";
}

function setMessage(copyKey) {
  state.lastMessageKey = copyKey || "";
  messageNode.textContent = copyKey ? getCopy(copyKey) : "";
}

function getInitialTheme() {
  const storedTheme = window.localStorage.getItem(THEME_STORAGE_KEY);

  if (storedTheme && THEMES[storedTheme]) {
    return storedTheme;
  }

  return "sunset";
}

function updateThemeButtons() {
  themeButtons.forEach(function (button) {
    const isActive = button.dataset.themeOption === state.currentTheme;
    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-pressed", String(isActive));
  });
}

function applyTheme(themeName) {
  const nextTheme = THEMES[themeName] ? themeName : "sunset";
  state.currentTheme = nextTheme;
  document.body.dataset.theme = nextTheme;

  if (themeColorMeta) {
    themeColorMeta.setAttribute("content", THEMES[nextTheme].color);
  }

  updateThemeButtons();
}

function setTheme(themeName) {
  applyTheme(themeName);
  window.localStorage.setItem(THEME_STORAGE_KEY, state.currentTheme);
}

function setThemePanelOpen(isOpen) {
  themeSwitcher.dataset.open = String(isOpen);
  themeTrigger.setAttribute("aria-expanded", String(isOpen));
  themePanel.hidden = !isOpen;
}

function getChunkSize() {
  const width = window.innerWidth;

  if (width < MOBILE_BREAKPOINT) {
    return 4;
  }

  if (width < TABLET_BREAKPOINT) {
    return 5;
  }

  if (width < DESKTOP_BREAKPOINT) {
    return 8;
  }

  return 10;
}

function renderRange(startNumber, endNumber) {
  resultNode.innerHTML = "";
  const chunkSize = getChunkSize();

  resultNode.style.setProperty("--result-columns", String(chunkSize));

  const letters = [];
  for (let current = startNumber; current <= endNumber; current += 1) {
    letters.push(numberToLetters(current));
  }

  for (let index = 0; index < letters.length; index += chunkSize) {
    const chunk = letters.slice(index, index + chunkSize);
    const block = document.createElement("section");
    block.className = "result-block";

    const labelRow = document.createElement("div");
    labelRow.className = "result-row";

    const numberRow = document.createElement("div");
    numberRow.className = "result-row";

    chunk.forEach(function (letter, offset) {
      const labelCell = document.createElement("div");
      labelCell.className = "cell";
      labelCell.textContent = letter.toUpperCase();

      const numberCell = document.createElement("div");
      numberCell.className = "cell num";
      numberCell.textContent = index + offset + 1;

      labelRow.appendChild(labelCell);
      numberRow.appendChild(numberCell);
    });

    block.appendChild(labelRow);
    block.appendChild(numberRow);
    resultNode.appendChild(block);
  }
}

function generateTable() {
  clearOutput();

  const startValue = startInput.value.trim();
  const endValue = endInput.value.trim();

  if (!isValidLetters(startValue) || !isValidLetters(endValue)) {
    setMessage("errorFormat");
    state.lastRange = null;
    return;
  }

  const startNumber = lettersToNumber(startValue);
  const endNumber = lettersToNumber(endValue);

  if (startNumber > MAX_VALUE || endNumber > MAX_VALUE) {
    setMessage("errorLimit");
    state.lastRange = null;
    return;
  }

  if (startNumber > endNumber) {
    setMessage("errorOrder");
    state.lastRange = null;
    return;
  }

  state.lastRange = { startNumber, endNumber };
  renderRange(startNumber, endNumber);
}

function resetTool() {
  startInput.value = "";
  endInput.value = "";
  state.lastRange = null;
  clearOutput();
  startInput.focus();
}

function handleEnter(event) {
  if (event.key === "Enter") {
    generateTable();
  }
}

function rerenderForViewport() {
  if (state.lastRange) {
    renderRange(state.lastRange.startNumber, state.lastRange.endNumber);
  }
}

function handleThemeTriggerClick() {
  const isOpen = themeSwitcher.dataset.open === "true";
  setThemePanelOpen(!isOpen);
}

function handleThemeOptionClick(event) {
  const nextTheme = event.currentTarget.dataset.themeOption;
  setTheme(nextTheme);
  setThemePanelOpen(false);
}

function handleDocumentClick(event) {
  if (!themeSwitcher.contains(event.target)) {
    setThemePanelOpen(false);
  }
}

function handleDocumentKeydown(event) {
  if (event.key === "Escape") {
    setThemePanelOpen(false);
  }
}

window.addEventListener("DOMContentLoaded", function () {
  applyTheme(getInitialTheme());
  setThemePanelOpen(false);

  window.setupI18n(excelColumnHelperTranslations, {
    onLanguageChange: function (language) {
      state.currentLanguage = language;

      if (state.lastRange) {
        renderRange(state.lastRange.startNumber, state.lastRange.endNumber);
      }

      setMessage(state.lastMessageKey);
    }
  });

  generateButton.addEventListener("click", generateTable);
  resetButton.addEventListener("click", resetTool);
  startInput.addEventListener("keydown", handleEnter);
  endInput.addEventListener("keydown", handleEnter);
  themeTrigger.addEventListener("click", handleThemeTriggerClick);
  themeButtons.forEach(function (button) {
    button.addEventListener("click", handleThemeOptionClick);
  });
  document.addEventListener("click", handleDocumentClick);
  document.addEventListener("keydown", handleDocumentKeydown);
  window.addEventListener("resize", rerenderForViewport);
});
