(function () {
  const STORAGE_KEY = "productivity-tools-language";

  function getInitialLanguage(translations) {
    const supported = Object.keys(translations);
    const stored = window.localStorage.getItem(STORAGE_KEY);

    if (stored && supported.includes(stored)) {
      return stored;
    }

    const browserLanguage = window.navigator.language || "";
    const match = supported.find((lang) => browserLanguage.toLowerCase().startsWith(lang.toLowerCase().slice(0, 2)));

    return match || supported[0];
  }

  function applyLanguage(translations, lang) {
    const table = translations[lang];
    document.documentElement.lang = lang;

    document.querySelectorAll("[data-i18n]").forEach((node) => {
      const key = node.dataset.i18n;
      if (table[key] !== undefined) {
        node.textContent = table[key];
      }
    });

    document.querySelectorAll("[data-i18n-html]").forEach((node) => {
      const key = node.dataset.i18nHtml;
      if (table[key] !== undefined) {
        node.innerHTML = table[key];
      }
    });

    document.querySelectorAll("[data-i18n-placeholder]").forEach((node) => {
      const key = node.dataset.i18nPlaceholder;
      if (table[key] !== undefined) {
        node.setAttribute("placeholder", table[key]);
      }
    });

    document.querySelectorAll("[data-i18n-aria-label]").forEach((node) => {
      const key = node.dataset.i18nAriaLabel;
      if (table[key] !== undefined) {
        node.setAttribute("aria-label", table[key]);
      }
    });

    if (table.pageTitle) {
      document.title = table.pageTitle;
    }

    const label = table.langToggle || (lang === "zh-TW" ? "EN" : "中文");
    document.querySelectorAll("[data-language-toggle]").forEach((button) => {
      button.textContent = label;
    });
  }

  window.setupI18n = function setupI18n(translations, options = {}) {
    let currentLanguage = getInitialLanguage(translations);

    function setLanguage(nextLanguage) {
      currentLanguage = nextLanguage;
      window.localStorage.setItem(STORAGE_KEY, currentLanguage);
      applyLanguage(translations, currentLanguage);

      if (typeof options.onLanguageChange === "function") {
        options.onLanguageChange(currentLanguage);
      }
    }

    document.querySelectorAll("[data-language-toggle]").forEach((button) => {
      button.addEventListener("click", function () {
        const available = Object.keys(translations);
        const nextLanguage = currentLanguage === available[0] ? available[1] : available[0];
        setLanguage(nextLanguage);
      });
    });

    setLanguage(currentLanguage);

    return {
      getLanguage: function () {
        return currentLanguage;
      },
      setLanguage
    };
  };
})();
