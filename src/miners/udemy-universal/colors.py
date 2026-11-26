"""Terminal text color definitions using the colorama library.

This module initializes colorama and provides convenient shorthand
variables for foreground, background, and style codes to be used
for coloring terminal output.

colorama is optional: in uv.lock it is only a Windows dependency, so on
Linux (the CI runner, the production image) it is not installed. Without it
every shorthand below is an empty string and the output is simply uncolored.
"""

# TODO: Standardize the code with the other projects. Current code has been migrated from other project.

# Optional dependency: colored terminal output.
try:
    from colorama import Back, Fore, Style, init

    init(autoreset=True)
    HAS_COLORAMA = True
except ImportError:
    HAS_COLORAMA = False


class _Plain:
    """Stand-in for a colorama class: every attribute is an empty string."""

    def __getattr__(self, name: str) -> str:
        return ""


if not HAS_COLORAMA:
    Fore = Back = Style = _Plain()
# colors foreground text:
fc = Fore.CYAN
fg = Fore.GREEN
fw = Fore.WHITE
fr = Fore.RED
fb = Fore.BLUE
flb = Fore.LIGHTBLUE_EX
fbl = Fore.BLACK
fy = Fore.YELLOW
fm = Fore.MAGENTA
flg = Fore.LIGHTGREEN_EX

# colors background text:
bc = Back.CYAN
bg = Back.GREEN
bw = Back.WHITE
br = Back.RED
bb = Back.BLUE
by = Back.YELLOW
bm = Back.MAGENTA

# colors style text:
sd = Style.DIM
sn = Style.NORMAL
sb = Style.BRIGHT
