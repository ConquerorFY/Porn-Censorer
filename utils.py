import pprint

pp = pprint.PrettyPrinter(indent=1, width=80, depth=None)

def print(args: str):
    pp.pprint(args)