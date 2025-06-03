"""Terminal text color definitions using the colorama library.

This module initializes colorama and provides convenient shorthand
variables for foreground, background, and style codes to be used
for coloring terminal output.
"""
# TODO: Standardize the code with the other projects. Current code has been migrated from other project.


from colorama import Back, Fore, Style, init

init(autoreset=True)
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
