# Lab 5 reflection: what I ran, what it found, how I fixed it

The assigned file is `ecommerce_cart_system.py`, one script of 83 lines. It keeps the cart
in a module level dictionary, adds and removes items, works out a discounted price, hashes
an item id, makes a checkout PIN and writes the cart to `receipt.txt`.

I ran the program before opening any tool. It exited with 0 and printed seven lines, so
nothing looked broken. That is the point worth remembering here: every problem written up
below was invisible to a normal run.

I ran each tool on its own and saved the output to a text file, first on the original code
and then again after the fixes. Those six files are in `reports/before/` and
`reports/after/`.

| tool | first run | last run |
|---|---|---|
| Pylint | 3.86/10, 35 messages | 10.00/10, 0 messages |
| Bandit | 5 findings (2 high, 1 medium, 2 low) | no issues identified |
| Flake8 | 7 findings | no findings |

---

## Pylint

```bash
pylint ecommerce_cart_system.py > reports/before/pylint_report.txt
```

Score was 3.86/10 from 35 messages. Most of them were convention and naming, but three
were real bugs and those are what I started with.

**A default argument that is shared between calls (W0102, line 15).** The signature was
`addItemToCart(item_id, name, price, qty=1, audit_log=[])`. Python builds that list once,
when the function is defined, so every call that leaves `audit_log` out appends to the same
list. Entries from one call show up in the next one, and two tests in the same process see
each other's log. It never goes wrong in this demo because `main()` only calls the function
once, which is why I needed a tool to spot it. I changed the default to `None` and create
the list inside:

```python
def add_item_to_cart(item_id, name, price, qty=1, audit_log=None):
    if audit_log is None:
        audit_log = []
```

**A bare `except` (W0702, lines 26 to 29).** `removeItemFromCart` wrapped a `del` in
`try: ... except: pass`. A bare except catches everything, including `KeyboardInterrupt` and
any typo I introduce later, and the `pass` means the caller never learns the removal failed.
I deleted the whole block and used `dict.pop` with a default:

```python
return cart_items.pop(item_id, None) is not None
```

Missing keys are now reported by the return value instead of being swallowed.

**A variable that was "unused" but actually was not (W0612, line 43).** Pylint said
`base_price` was assigned and never used, which looked wrong because the discount clearly
depends on it. The catch is that the use was hidden inside the string passed to `eval`:
`eval("base_price * 0.90")`. So the variable was only used at runtime, and a reader of the
function body cannot see that. Once `eval` was gone (see Bandit below) `base_price` became
a normal variable again.

The rest of the Pylint list, briefly:

- **`global total_sales` (W0603, lines 12 and 16).** Module level mutable state changed
  from inside a function. I moved the counter into `TOTAL_SALES = {"amount": 0.0}` and
  update it through a small `_record_sale()` helper, so no `global` keyword is needed and
  `get_total_sales()` gives tests a way to read it.
- **Naming (C0103).** Eight functions were camelCase (`addItemToCart`,
  `calculateDiscountedTotal`, and so on) and the module constant was `total_sales`. I
  renamed all of them to snake case and updated the calls in `main()`. This is the change
  that moved the score the most and it changes no behaviour at all.
- **Docstrings (C0114, C0116).** No module docstring and no function docstrings. I added a
  module docstring and a one line docstring per function that says what it returns,
  because `checkCartStatus` and `getCartSummary` were ambiguous names on their own.
- **File handling (W1514, R1732, lines 57 to 59).** `open()` used with no encoding and a
  manual `close()`. Changed to `with open(filename, "w", encoding="utf-8") as receipt:`.
  The encoding matters: without it the receipt bytes depend on the platform.
- **`== None` (C0121, line 34).** Changed to `is None`. I also collapsed the
  `if ... return True else: return False` below it (R1703, R1705) into one early return:
  `return item["qty"] > 0`.
- **Dead code.** `handling_fee = 4.50` was never used (W0612) and `import math` was never
  used (W0611). Both deleted. The unused loop key `k` in `getCartSummary` went away when I
  replaced the loop with `sum(item["qty"] for item in items.values() if item["qty"] > 0)`.
- **Small ones.** `%` formatting on line 21 became an f-string (C0209), and the parameter
  `cart_items` in `getCartSummary` shadowed the module level `cart_items` (W0621) so I
  renamed the parameter to `items`.

After this commit the score was 9.81/10. The two messages left were the missing final
newline and one long line, which I dealt with under Flake8.

---

## Bandit

```bash
bandit -r ecommerce_cart_system.py > reports/before/bandit_report.txt
```

Five findings: two high, one medium, two low. These were the ones I did first, before any
style work, because they are exploitable rather than untidy.

**`os.system` with a string built from an argument (B605, line 60, high).** The line was
`os.system("echo Receipt saved to: " + filename)`. The filename goes straight into a shell
command, so `exportCartReceipt("x; rm -rf ~")` would run whatever came after the semicolon.
There was no reason to use a shell at all, so it is a `print` now:

```python
print(f"Receipt saved to: {filename}")
```

**MD5 for the item hash (B324, line 49, high).** MD5 collisions are cheap to produce, so an
"item fingerprint" built with it can be forged. Swapped to `hashlib.sha256`, keeping the
same function name and return type. I also made the encoding explicit, since
`item_id.encode()` without one depends on the platform default.

**`eval` on a string (B307, line 44, medium; Pylint flagged it too as W0123).** The function
took a string and evaluated it, so
`calculateDiscountedTotal("ITEM1", "__import__('os').system('...')")` runs code. The usual
answer from Bandit is `ast.literal_eval`, but that cannot work here, because the demo passed
`"base_price * 0.90"`, which is an expression and not a literal. So I changed the contract
of the function instead: it now takes a percentage, checks the range and does the maths.

```python
def calculate_discounted_total(item_id, discount_percent):
    base_price = cart_items[item_id]["price"]
    discount = float(discount_percent)
    if not 0 <= discount <= 100:
        raise ValueError("discount_percent must be between 0 and 100")
    return round(base_price * (1 - discount / 100), 2)
```

The call in `main()` became `calculate_discounted_total("ITEM1", 10)`. Output is still
`22.5`, but the caller can no longer hand the function code to run. This was the only fix
that needed an API change rather than a local edit.

**`random.randint` for the PIN (B311, line 53, low).** `random` is a Mersenne Twister and
its state can be recovered from a few outputs, so a PIN from it is guessable. Replaced with
`secrets.randbelow(9000) + 1000`, which keeps the same four digit range.

**`try` / `except` / `pass` (B110, lines 26 to 29, low).** The same block Pylint reported.
Fixed once, in this commit, with `dict.pop`.

Bandit came back with "No issues identified" after this commit, and that has held on every
run since.

---

## Flake8

```bash
flake8 ecommerce_cart_system.py > reports/before/flake8_report.txt
```

Seven findings on the first run: `F401` for the unused `math` import, `E722` for the bare
except, `F841` twice (for `handling_fee` and `base_price`), `E711` for `== None`, `E501` for
an 86 character line on line 76, and `W292` for no newline at the end of the file.

Four of those seven were already gone by the time I got here, because Flake8 was pointing at
the same code Pylint and Bandit had flagged. `E722` and one `F841` went with the Bandit
commit, and `F401`, `E711` and the other `F841` went with the Pylint commit. That left two
real style items for the third commit, which is why it is the smallest of the three.

**Long line (E501).** The line was
`print("Gateway secret:", "configured" if payment_gateway_key else "not configured")`,
87 characters with the CRLF counted. Split it and shortened the local variable name:

```python
key_state = "configured" if gateway_key else "not configured"
print("Gateway secret:", key_state)
```

**No newline at the end (W292, and Pylint C0304).** The file simply stopped after `main()`.
Added the newline. While checking I also confirmed nothing was over 79 characters:

```bash
tr -d '\r' < ecommerce_cart_system.py | awk 'length > 79 {print NR": "length}'
```

Flake8 prints nothing at all on the final file, which is what an empty
`reports/after/flake8_report.txt` means.

---

## Bugs that none of the three tools caught

This was the part I did not expect. The tools cover the rules they have, and a few real
problems in this file are outside all of them.

**A live payment key in the source (line 72).** `payment_gateway_key = "STRIPE_SECRET_KEY_LIVE_2026"`
was hard coded, and `main()` printed it on the last line of output, so the secret would sit
in console scrollback, terminal logs and CI output. Bandit's B105 did not fire because the
variable name does not match the password and secret patterns it looks for. I changed it to
`os.environ.get("PAYMENT_GATEWAY_KEY")` and the script now prints only whether the key is
configured.

**`%d` used to format a float price (line 21).** `"Added %s with price %d" % (item_id, price)`
truncates, so an item at 35.50 was logged as `35`. Nothing flags it because it is valid
formatting, just the wrong one. The f-string uses `{price:.2f}` now.

**The sales total never goes down (lines 20 and 27).** `total_sales` is increased when an
item is added and never decreased when one is removed, so it drifts away from the real cart
contents. I wrote it up in `issues.md` but did not change it, because doing so changes what
the function reports and this lab is about the tool findings. The refactor for the `global`
statement at least makes the fix a one liner later.

**No `if __name__ == "__main__":` guard (line 84).** Importing the module runs the whole
demo, writes `receipt.txt` and prints a PIN. I left it alone so the script behaves exactly
as it did before, and noted it as a known improvement.

---

## Where it ended up

Pylint 10.00/10, Bandit reporting no issues, Flake8 reporting nothing, and
`python ecommerce_cart_system.py` still prints the same seven lines it printed at the
start. The security change that matters most, removing `eval`, cost nothing in output
because I kept the numbers identical for the demo input.

One thing I decided early: no `# pylint: disable` and no `# noqa` anywhere in the final
file. Renaming the eight camelCase functions took longer than adding a disable comment
would have, but a disable comment just hides the finding from whoever reads the code next.
