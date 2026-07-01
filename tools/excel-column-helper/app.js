const excelColumnHelperTranslations = {
  "zh-TW": {
    pageTitle: "Excel 欄位對照工具",
    brand: "Tool / Excel",
    backHome: "回到首頁",
    eyebrow: "Excel utility",
    title: "Excel 欄位對照工具",
    intro: "輸入起始與結束欄位，例如 <strong>A</strong> 到 <strong>AC</strong>，工具會展開欄位名稱與欄位序號。",
    startLabel: "起始欄位",
    endLabel: "結束欄位",
    startPlaceholder: "例如 A",
    endPlaceholder: "例如 AC",
    generate: "產生對照表",
    reset: "重設",
    footnote: "支援 Excel 最大欄位 XFD，並以每列 10 欄顯示結果。",
    errorFormat: "請輸入 1 到 3 個英文字母。",
    errorLimit: "Excel 欄位上限是 XFD。",
    errorOrder: "起始欄位不能大於結束欄位。"
  },
  en: {
    pageTitle: "Excel Column Helper",
    brand: "Tool / Excel",
    backHome: "Back home",
    eyebrow: "Excel utility",
    title: "Excel Column Helper",
    intro: "Enter a start and end column, such as <strong>A</strong> to <strong>AC</strong>, and the tool will expand the labels and numeric positions.",
    startLabel: "Start column",
    endLabel: "End column",
    startPlaceholder: "For example A",
    endPlaceholder: "For example AC",
    generate: "Generate table",
    reset: "Reset",
    footnote: "Supports Excel columns up to XFD and shows results in groups of 10.",
    errorFormat: "Please enter 1 to 3 letters.",
    errorLimit: "The maximum Excel column is XFD.",
    errorOrder: "The start column cannot be after the end column."
  }
};

const state = {
  currentLanguage: "zh-TW",
  lastRange: null,
  lastMessageKey: ""
};

const startInput = document.getElementById("start");
const endInput = document.getElementById("end");
const messageNode = document.getElementById("message");
const resultNode = document.getElementById("result");
const generateButton = document.getElementById("generateButton");
const resetButton = document.getElementById("resetButton");
const MAX_VALUE = lettersToNumber("xfd");

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

function renderRange(startNumber, endNumber) {
  resultNode.innerHTML = "";

  const letters = [];
  for (let current = startNumber; current <= endNumber; current += 1) {
    letters.push(numberToLetters(current));
  }

  for (let index = 0; index < letters.length; index += 10) {
    const chunk = letters.slice(index, index + 10);
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
      numberCell.textContent = index + offset + startNumber;

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

window.addEventListener("DOMContentLoaded", function () {
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
});
