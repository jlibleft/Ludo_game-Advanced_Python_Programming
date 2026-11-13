"""Shared visual styling for the desktop interface."""

APPLICATION_STYLE = """
QWidget {
    color: #24334b;
    font-family: "Segoe UI", "DejaVu Sans", sans-serif;
    font-size: 14px;
}
QMainWindow, QWidget#centralArea {
    background-color: #f4f6fa;
}
QLabel#title {
    font-size: 30px;
    font-weight: 700;
}
QLabel#subtitle {
    color: #66758a;
    font-size: 14px;
}
QStatusBar {
    background-color: #ffffff;
    border-top: 1px solid #e2e7ef;
    color: #66758a;
}
"""
