def yes_no_loop(prompt: str) -> str:
    """
    Force the user to say yes, no, or get some feedback
    """
    print(prompt)
    user_input = input("Your response [y/n]: ")
    while user_input.lower() not in ["y", "n"]:
        user_input = input("Your response (must be 'y' or 'n'): ")
    return "yes" if user_input.lower() == "y" else "no"
