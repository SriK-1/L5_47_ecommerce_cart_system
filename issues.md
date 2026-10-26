# Issue Log - `ecommerce_cart_system.py`

Static analysis lab, Pylint + Bandit + Flake8.

- **File:** `ecommerce_cart_system.py`, 83 lines in the original version
- **Tools:** Pylint 4.1.3, Bandit 1.9.4, Flake8 7.4.1 (pycodestyle 2.15.0, pyflakes 4.0.3), Python 3.13
- **Reports:** `reports/before/` for the original file, `reports/after/` for the fixed one
- **Line numbers:** they all refer to the original file, as committed in `29fd6c1`

25 problems are written up below. 21 of them came from the tools and 4 came from reading
the code and its output. The tool number is lower than the raw message count because the
three tools report the same code more than once, for example the bare `except` is reported
by all three of them. The 4 that no tool flagged are marked as such in the table.

## Score summary

| Tool | Before | After |
|------|--------|-------|
| Pylint | 3.86 / 10, 35 messages | 10.00 / 10, 0 messages |
| Bandit | 5 issues (2 High, 1 Medium, 2 Low) | 0 issues |
| Flake8 | 7 issues (F401, E722, F841 x2, E711, E501, W292) | 0 issues |

---

## 1. High and medium severity findings, fixed first

| Issue | Type | Line(s) | Description | Fix Approach |
|-------|------|---------|-------------|--------------|
| `os.system("echo " + filename)`, Bandit **B605** `start_process_with_a_shell` | Security (High) | 60 | The filename is joined into a shell command. A name like `x; rm -rf ~` is executed by the shell, which is command injection (CWE-78). | Replaced with `print(f"Receipt saved to: {filename}")`. Nothing needs a subprocess here, so nothing reaches a shell any more. |
| `hashlib.md5()` for item fingerprints, Bandit **B324** `hashlib` | Security (High) | 49 | MD5 is broken and collisions are cheap, so the "fingerprint" can be forged (CWE-327). | Switched to `hashlib.sha256(item_id.encode("utf-8"))`. Same function name and same return type. |
| Hard coded `STRIPE_SECRET_KEY_LIVE_2026` in `main()`, **not flagged by any tool** | Security (High) | 72 | A live payment key is committed to the repo and also printed to stdout, so it ends up in console logs and CI output. Bandit's B105 did not fire because the variable name does not match its password and secret patterns. | Read it with `os.environ.get("PAYMENT_GATEWAY_KEY")` and print only whether it is configured. The value goes in `.env`, not in git. |
| `eval(discount_expr)`, Bandit **B307**, Pylint **W0123** | Security (Medium) | 44 | `eval` runs whatever Python is in the string, so it is remote code execution (CWE-78). `ast.literal_eval` cannot replace it here because the demo passes `"base_price * 0.90"`, which is an expression and not a literal. | `eval` removed. The function takes a numeric `discount_percent`, validates `0 <= discount <= 100` and returns `price * (1 - discount/100)`. |
| Mutable default argument `audit_log=[]`, Pylint **W0102** | Bug (High) | 15 | The default list is built once when the function is defined and then shared, so audit entries leak between calls and between tests. | Default changed to `None`, with `if audit_log is None: audit_log = []` inside the function. |
| `try: del ... except: pass`, Bandit **B110**, Pylint **W0702**, Flake8 **E722** | Bug (Medium) | 26-29 | The bare `except` swallows every error, including `KeyboardInterrupt`, and `pass` means the caller never learns the removal failed (CWE-703). | Block deleted. `return cart_items.pop(item_id, None) is not None` reports missing keys through the return value. |
| `base_price` assigned but never read by the code, Pylint **W0612**, Flake8 **F841** | Bug (Medium) | 43 | The variable is only used inside the `eval` string, so the function depends on a name that exists at runtime but not in the code. | Once `eval` was gone, `base_price` became a normal variable used in the discount calculation. |

## 2. Low severity, code smells and style

| Issue | Type | Line(s) | Description | Fix Approach |
|-------|------|---------|-------------|--------------|
| `random.randint()` for the checkout PIN, Bandit **B311** | Security (Low) | 53 | `random` is a Mersenne Twister and its state can be recovered from a few outputs, so the PIN is predictable (CWE-330). | `secrets.randbelow(9000) + 1000`, the standard library CSPRNG. |
| `%d` used to format a float price, **not flagged by any tool** | Bug (Low) | 21 | `"price %d" % 35.5` truncates, so the audit log records `35` for an item that costs 35.50. | Changed to `f"Added {item_id} with price {price:.2f}"`. |
| `total_sales` never decreases, **not flagged by any tool** | Bug (Low) | 20, 27 | The counter goes up when an item is added and is never corrected when one is removed, so it drifts away from the cart. It is hidden because the demo never prints the counter. | Documented, not changed. Reversing the entry would change the original behaviour. The new `_record_sale()` helper makes the fix a one liner later. |
| `global total_sales`, Pylint **W0603** | Code smell (Low) | 12, 16 | Module wide mutable state changed from inside a function. Hard to test and hard to reason about. | The counter lives in `TOTAL_SALES = {"amount": 0.0}`, updated by `_record_sale()` and read by `get_total_sales()`. No `global` statement left. |
| `open()` with no encoding and no context manager, Pylint **W1514**, **R1732** | Code smell (Low) | 57-59 | The encoding depends on the platform, so receipts differ between Windows and Linux, and a manual `close()` leaks the handle if `write()` raises. | `with open(filename, "w", encoding="utf-8") as receipt:` |
| `handling_fee = 4.50` never used, Pylint **W0612**, Flake8 **F841** | Code smell (Low) | 33 | Dead local from an earlier version. It makes the reader think a fee is being applied. | Deleted. |
| `cart_items.get(item_id) == None`, Pylint **C0121**, Flake8 **E711** | Style (Low) | 34 | Comparison with `None` should use identity, `is None`. | Rewritten as `item = cart_items.get(item_id)` followed by `if item is None: return False`. |
| `if ... return True else: return False`, Pylint **R1703**, **R1705** | Style (Low) | 36-39 | Redundant boolean branches plus an `else` after a `return`. | Early return, then `return item["qty"] > 0`. |
| camelCase function names, Pylint **C0103** | Style (Low) | 15, 25, 32, 42, 48, 52, 56, 63 | Eight functions violate PEP 8 (`addItemToCart`, `calculateDiscountedTotal`, ...). | Renamed to snake case and the calls in `main()` updated. |
| `total_sales` constant naming, Pylint **C0103** | Style (Low) | 12 | A module level name should be UPPER_CASE. | Renamed to `TOTAL_SALES`. The structure also changed, see the `global` row. |
| Module and function docstrings missing, Pylint **C0114**, **C0116** | Style (Low) | 1, 15, 25, 32, 42, 48, 52, 56, 63, 71 | Nothing says what the module or the functions do. `checkCartStatus` and `getCartSummary` are ambiguous names on their own. | Module docstring added, plus a one line docstring per function stating purpose and return contract. |
| `import math` never used, Pylint **W0611**, Flake8 **F401** | Style (Low) | 4 | Leftover import. | Removed. |
| Parameter `cart_items` shadows the module global, Pylint **W0621** | Style (Low) | 63 | The parameter has the same name as the global, so a change inside the function silently ignores the real cart. | Parameter renamed to `items`. |
| Unused loop key `k`, Pylint **W0612** | Style (Low) | 65 | Only the values are used. | Loop replaced with `sum(item["qty"] for item in items.values() if item["qty"] > 0)`. |
| `%` formatting instead of an f-string, Pylint **C0209** | Style (Low) | 21 | Legacy formatting, harder to read and to change later. | Converted to an f-string. |
| Line too long, 86 > 79 characters, Flake8 **E501** | Style (Low) | 76 | PEP 8 line length. | The gateway message is split over two lines and the local is renamed to `gateway_key`. |
| No newline at end of file, Flake8 **W292**, Pylint **C0304** | Style (Low) | 84 | POSIX text file convention, and it makes diffs noisy. | The file now ends with a single newline. |
| No `if __name__ == "__main__":` guard, **not flagged by any tool** | Code smell (Low) | 84 | Importing the module runs the demo, writes `receipt.txt` and prints a PIN. | Documented, not changed. The lab runs the file as a script and I kept the original entry point so the output stays the same. |

---

## Verification

```bash
python3 -m venv venv
source venv/bin/activate
pip install pylint bandit flake8

# before the fixes
pylint ecommerce_cart_system.py   > reports/before/pylint_report.txt
bandit -r ecommerce_cart_system.py > reports/before/bandit_report.txt
flake8 ecommerce_cart_system.py   > reports/before/flake8_report.txt

# after the three fix commits
pylint ecommerce_cart_system.py   > reports/after/pylint_report.txt
bandit -r ecommerce_cart_system.py > reports/after/bandit_report.txt
flake8 ecommerce_cart_system.py   > reports/after/flake8_report.txt
```

| Check | Result |
|-------|--------|
| Pylint on the final file | `Your code has been rated at 10.00/10`, target was above 9.5 |
| Bandit on the final file | `No issues identified.` with High 0, Medium 0, Low 0 |
| Flake8 on the final file | no output and exit code 0 |
| Program still works | `python ecommerce_cart_system.py` prints the same 7 lines as before, exit code 0 |

The fixes are in three commits, one per tool:

```
b5f8a93 Fix Flake8/PEP 8 style violations (7 -> 0 findings)
7c1167b Fix code-quality and design issues flagged by Pylint (score 3.86 -> 9.81)
8874ea5 Fix security issues flagged by Bandit (B110, B307, B324, B311, B605)
```
