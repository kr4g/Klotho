// Shared loop-button controller for Klotho playback widgets.
// Installs globalThis.KlothoLoopControl once; every widget (animated
// figures, SuperSonic engine) builds its loop state and
// button behavior through this factory so the loop policy semantics
// (off / infinite toggle / finite re-armed cycle count) stay identical.
// KlothoGateToggle: the play button renders disabled/greyed (see
// control_bar_html) and is enabled when the engine-ready promise settles.
// It re-enables on failure too — with a tooltip hint — so a click can
// retry the boot instead of leaving a dead control.
(function () {
    if (typeof globalThis.KlothoGateToggle === "function") return;
    globalThis.KlothoGateToggle = function (toggleBtn, readyPromise) {
        if (!toggleBtn) return;
        function restore(ok) {
            toggleBtn.disabled = false;
            toggleBtn.style.opacity = "1";
            toggleBtn.style.cursor = "pointer";
            if (ok) toggleBtn.removeAttribute("title");
            else toggleBtn.title = "Audio engine not ready — click to retry";
        }
        Promise.resolve(readyPromise).then(restore, function () { restore(false); });
    };
})();

(function () {
    if (typeof globalThis.KlothoLoopControl === "function") return;
    globalThis.KlothoLoopControl = function (btn, svg, mode, count, enabled) {
        var infinite = mode !== "finite";
        var finiteCount = mode === "finite" ? Math.max(2, Math.floor(Number(count) || 0)) : 0;
        var ctl = {
            enabled: !!enabled,
            infinite: infinite,
            finiteCount: finiteCount,
            cyclesRemaining: finiteCount,
            onToggle: null,
            // Value for scheduler/player `loop` options: true (endless),
            // a cycle count, or false.
            schedulerValue: function () {
                return ctl.enabled ? (infinite ? true : finiteCount) : false;
            },
            rearm: function () {
                if (!infinite) ctl.cyclesRemaining = finiteCount;
            },
            sync: function () {
                if (!btn) return;
                if (mode === "off") {
                    btn.style.opacity = "0.3";
                    btn.style.cursor = "not-allowed";
                    if (svg) svg.setAttribute("stroke", "#666");
                    return;
                }
                btn.style.opacity = ctl.enabled ? "1" : "0.5";
                btn.style.cursor = "pointer";
                if (svg) svg.setAttribute("stroke", ctl.enabled ? "#4ade80" : "#a0a0a0");
            },
        };
        if (btn) {
            btn.addEventListener("click", function () {
                if (mode === "off") return;
                ctl.enabled = !ctl.enabled;
                ctl.rearm();
                ctl.sync();
                if (ctl.onToggle) ctl.onToggle(ctl.enabled);
            });
        }
        ctl.sync();
        return ctl;
    };
})();
