from booktool.util import is_sanitized, sanitize

# data maps raw value(s) to the proper sanitized output
data = [
    (["J. K. Rowling", "J.K.Rowling", "J K Rowling"], "J_K_Rowling"),
    (["Jon Kabat-Zinn"], "Jon_KabatZinn"),
    (["And Yet..."], "And_Yet"),
    (["Infinite Jest (Abridged)"], "Infinite_Jest-Abridged"),
    (
        ["The Information: A History, a Theory, a Flood"],
        "The_Information-A_History_a_Theory_a_Flood",
    ),
    (["The Time Traveler's Wife"], "The_Time_Travelers_Wife"),
]


def test_data():
    for _, output in data:
        assert is_sanitized(output)


def test_sanitize():
    for inputs, output in data:
        for value in inputs:
            assert sanitize(value) == output
