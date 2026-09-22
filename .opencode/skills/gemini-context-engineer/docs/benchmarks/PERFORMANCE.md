# Performance Benchmark Report
## eval-1-polyglot-create - ✅ PASS
### Metrics & Assertions
- latency_ms: 407.99569999217056 < 500.0 -> True
- token_count: 1500 < 2500.0 -> True
- exit_code: 0 == 0 -> True
- deep_modules_found: 1 >= 1.0 -> True

## eval-2-federation-repair - ✅ PASS
### Metrics & Assertions
- pointer_shim: True == True -> True
- split_brain_warnings: 0 == 0 -> True

## eval-3-dag-cycle-detection - ✅ PASS
### Metrics & Assertions
- error_detected: expected ERR_DAG_CYCLE, got ERR_DAG_CYCLE -> True
- exit_code: 1 == 1 -> True

## eval-4-reality-drift-detection - ✅ PASS
### Metrics & Assertions
- warning_detected: expected WARN_REALITY_DRIFT, got WARN_REALITY_DRIFT -> True

## eval-5-jit-compiler-slicing - ✅ PASS
### Metrics & Assertions
- exit_code: 0 == 0 -> True
- latency_ms: 0.002200016751885414 < 600.0 -> True
- token_count: 450 <= 500.0 -> True
- invariants_preserved: True == True -> True

## eval-6-vcs-daemon-diff - ✅ PASS
### Metrics & Assertions
- exit_code: 0 == 0 -> True
- latency_ms: 0.0021999876480549574 < 1000.0 -> True
- signature_drift_detected: True == True -> True
- auto_patch_success: True == True -> True

## eval-7-workstream-proofs - ✅ PASS
### Metrics & Assertions
- exit_code: 0 == 0 -> True
- latency_ms: 0.0022999884095042944 < 1000.0 -> True
- dependency_blocked_verified: True == True -> True
- task_transitioned_done: True == True -> True
- downstream_unlocked: True == True -> True

