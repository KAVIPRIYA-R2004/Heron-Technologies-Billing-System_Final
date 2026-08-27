ONES = [
    "", "One", "Two", "Three", "Four", "Five",
    "Six", "Seven", "Eight", "Nine", "Ten",
    "Eleven", "Twelve", "Thirteen", "Fourteen",
    "Fifteen", "Sixteen", "Seventeen", "Eighteen",
    "Nineteen"
]

TENS = [
    "", "", "Twenty", "Thirty", "Forty",
    "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"
]


def number_to_words(num):
    num = int(num)

    if num < 20:
        return ONES[num]

    if num < 100:
        return TENS[num // 10] + (" " + ONES[num % 10] if num % 10 else "")

    if num < 1000:
        return (
            ONES[num // 100]
            + " Hundred"
            + (" " + number_to_words(num % 100) if num % 100 else "")
        )

    if num < 100000:
        return (
            number_to_words(num // 1000)
            + " Thousand"
            + (" " + number_to_words(num % 1000) if num % 1000 else "")
        )

    if num < 10000000:
        return (
            number_to_words(num // 100000)
            + " Lakh"
            + (" " + number_to_words(num % 100000) if num % 100000 else "")
        )

    return (
        number_to_words(num // 10000000)
        + " Crore"
        + (" " + number_to_words(num % 10000000) if num % 10000000 else "")
    )


def amount_in_words_inr(amount):
    amount = float(amount)

    rupees = int(amount)
    paise = round((amount - rupees) * 100)

    result = number_to_words(rupees) + " Rupees"

    if paise > 0:
        result += " and " + number_to_words(paise) + " Paise"

    return result + " Only"
