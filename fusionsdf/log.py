_console = None

def set_log_console(console):
    global _console
    _console = console

def log(message):
    if _console:
        _console.writeText(message)