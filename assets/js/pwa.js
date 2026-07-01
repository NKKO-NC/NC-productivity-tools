(function () {
  const script = document.currentScript;
  const swPath = script?.dataset?.sw || "./sw.js";
  const installButton = document.querySelector("[data-install-pwa]");
  let deferredInstallPrompt = null;

  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register(swPath).catch(function (error) {
        console.error("Service worker registration failed:", error);
      });
    });
  }

  window.addEventListener("beforeinstallprompt", function (event) {
    event.preventDefault();
    deferredInstallPrompt = event;

    if (installButton) {
      installButton.hidden = false;
    }
  });

  window.addEventListener("appinstalled", function () {
    deferredInstallPrompt = null;

    if (installButton) {
      installButton.hidden = true;
    }
  });

  if (installButton) {
    installButton.addEventListener("click", async function () {
      if (!deferredInstallPrompt) {
        return;
      }

      deferredInstallPrompt.prompt();
      await deferredInstallPrompt.userChoice;
      deferredInstallPrompt = null;
      installButton.hidden = true;
    });
  }
})();
