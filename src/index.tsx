import { useEffect, useSyncExternalStore } from "react";
import { addEventListener, definePlugin, removeEventListener, routerHook, toaster } from "@decky/api";
import { ButtonItem, Navigation, PanelSection, PanelSectionRow, staticClasses } from "@decky/ui";
import { FaGamepad } from "react-icons/fa";

import App from "./components/App";
import ErrorBoundary from "./components/ErrorBoundary";
import { checkUpdates } from "./api";
import { onJobDone } from "./actions";
import { refresh, setState, snapshot, subscribe } from "./state";
import { ago } from "./components/ui";

const ROUTE = "/emu-hub";

const Page = () => (
  <ErrorBoundary label="page">
    <App />
  </ErrorBoundary>
);

function Panel() {
  const state = useSyncExternalStore(subscribe, snapshot, snapshot);
  useEffect(() => {
    refresh().catch(() => undefined);
  }, []);
  const installed = state?.emulators.filter((emu) => emu.installed).length ?? 0;
  const running = state?.emulators.filter((emu) => emu.job && (emu.job.state === "queued" || emu.job.state === "running")) ?? [];

  const open = () => {
    Navigation.Navigate(ROUTE);
    Navigation.CloseSideMenus();
  };
  const check = () => {
    checkUpdates(true)
      .then((next) => {
        setState(next);
        toaster.toast({
          title: "Emu Hub",
          body: next.updates ? `${next.updates} update${next.updates === 1 ? "" : "s"} available` : "Everything is up to date",
        });
      })
      .catch((error) => toaster.toast({ title: "Update check failed", body: String(error) }));
  };

  return (
    <ErrorBoundary label="panel">
      <PanelSection title="Emu Hub">
        <PanelSectionRow>
          <ButtonItem layout="below" onClick={open}>
            {state?.updates ? `Open Emu Hub · ${state.updates} update${state.updates === 1 ? "" : "s"}` : "Open Emu Hub"}
          </ButtonItem>
        </PanelSectionRow>
        <PanelSectionRow>
          <ButtonItem layout="below" onClick={check} disabled={state?.checking}>
            {state?.checking ? "Checking…" : "Check for updates"}
          </ButtonItem>
        </PanelSectionRow>
        {state ? (
          <PanelSectionRow>
            <div style={{ fontSize: "12px", color: "#8f98a0", lineHeight: 1.6, width: "100%" }}>
              <div>{installed} emulators installed</div>
              {running.map((emu) => (
                <div key={emu.id}>
                  {emu.name}: {emu.job?.message} {Math.round((emu.job?.progress ?? 0) * 100)}%
                </div>
              ))}
              <div>Last check: {ago(state.checked_at)}</div>
              <div style={{ wordBreak: "break-all" }}>Library: {state.library.root}</div>
            </div>
          </PanelSectionRow>
        ) : null}
      </PanelSection>
    </ErrorBoundary>
  );
}

const onUpdates = (info: { count: number; names: string[] }) => {
  refresh().catch(() => undefined);
  toaster.toast({
    title: `${info.count} emulator update${info.count === 1 ? "" : "s"}`,
    body: info.names.join(", "),
    onClick: () => Navigation.Navigate(ROUTE),
  });
};

const onNotice = (title: string, body: string) => {
  refresh().catch(() => undefined);
  toaster.toast({ title, body });
};

const onJob = (event: Parameters<typeof onJobDone>[0]) => {
  onJobDone(event).catch(() => undefined);
};

export default definePlugin(() => {
  addEventListener("emuhub_updates", onUpdates);
  addEventListener("emuhub_notice", onNotice);
  addEventListener("emuhub_job", onJob);
  routerHook.addRoute(ROUTE, Page, { exact: true });

  return {
    name: "Emu Hub",
    titleView: <div className={staticClasses.Title}>Emu Hub</div>,
    content: <Panel />,
    icon: <FaGamepad />,
    onDismount() {
      removeEventListener("emuhub_updates", onUpdates);
      removeEventListener("emuhub_notice", onNotice);
      removeEventListener("emuhub_job", onJob);
      routerHook.removeRoute(ROUTE);
    },
  };
});
