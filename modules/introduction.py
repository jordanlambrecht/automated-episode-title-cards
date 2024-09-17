from rich.console import Console
from rich.align import Align
console = Console()
def introduction():

     console.print(Align.center(r"""

     █████╗   ███████╗ ████████╗  ██████╗      ██╗  ██╗ ██╗
     ██╔══██╗  ██╔════╝ ╚══██╔══╝ ██╔════╝     ██║  ██║ ██║
     ███████║  █████╗      ██║    ██║          ███████║ ██║
     ██╔══██║  ██╔══╝      ██║    ██║          ██╔══██║ ╚═╝
     ██║  ██║  ███████╗    ██║    ╚██████╗ ▄█╗ ██║  ██║ ██╗
     ╚═╝  ╚═╝  ╚══════╝    ╚═╝     ╚═════╝ ╚═╝ ╚═╝  ╚═╝ ╚═╝


          """, style="bold red"))
     
     console.print(Align.center(r"""
     ╔═══════════════════════════════════════════════════════════════════════════╗
     ║                                                                           ║
     ║                   Automated Episode Title Cards, Hooray!                  ║
     ║                                                                           ║
     ║                             (c) 2014, Jordy                               ║
     ║                                                                           ║
     ║                            Full Documentation:                            ║
     ║      https://github.com/jordanlambrecht/automated-episode-title-cards     ║
     ║                                                                           ║
     ╚═══════════════════════════════════════════════════════════════════════════╝
          """,style="bold yellow"))