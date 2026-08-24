# F5.12 — Walk-Forward Validation

Rolling folds are generated deterministically before the final holdout boundary. Every fold uses ExperimentRunner and isolated train/test instances with indicator-only warm-up; report PnL is OOS only. Parameters are pre-declared from the robustness region; no fold reoptimization occurs. The final holdout is excluded from fold generation and execution. Summary metrics measure positive-fold proportion, medians, dispersion and worst cases.
