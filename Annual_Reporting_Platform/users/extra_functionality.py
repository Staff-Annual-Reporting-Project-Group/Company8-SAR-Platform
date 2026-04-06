from better_profanity import profanity

profanity.load_censor_words()


def verify_title(s):
    if not s:
        return False

    s = s.strip()

    # Length check
    if len(s) < 5:
        return False

    # Profanity check
    if profanity.contains_profanity(s):
        return False

    return True


def verify_description(s):
    if not s:
        return False

    s = s.strip()

    # Length check
    if len(s) < 10:
        return False

    # Profanity check
    if profanity.contains_profanity(s):
        return False

    return True