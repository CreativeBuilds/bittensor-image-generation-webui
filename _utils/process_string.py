# process strings that have , in them, safe for csv
def process_string(string):
    
    # remove newlines
    string = string.replace("\n", "")
    # remove carriage returns
    string = string.replace("\r", "")
    # remove tabs
    string = string.replace("\t", "")

    if "," in string:
        return f"\"{string}\""
    return string