class UIConstants:
    WINDOW_WIDTH = 1200
    WINDOW_HEIGHT = 900
    MIN_WIDTH = 1000
    MIN_HEIGHT = 700
    
    CONTENT_MARGINS = (30, 20, 30, 20)
    CONTENT_SPACING = 15
    
    TEXT_BOX_HEIGHTS = {
        'source': 70,
        'target': 70,
        'edit': 90,
        'notes': 70
    }
    
    FONT_SIZES = {
        'title': 16,
        'label': 13,
        'text': 13,
        'button': 12
    }

STYLESHEET = """
QWidget#main_window {
    background-color: #FFFFFF;
}

QLabel#title_label {
    font-size: 16px;
    font-weight: bold;
    color: #333333;
    padding-top: 8px;
    padding-bottom: 4px;
}

QProgressBar {
    border: 1px solid #DDDDDD;
    border-radius: 8px;
    text-align: center;
    font-weight: bold;
    color: #333;
    height: 22px;
    margin-bottom: 30px;
}

QProgressBar::chunk {
    background-color: #4CAF50;
    border-radius: 8px;
}

QLabel#field_label {
    font-size: 13px;
    color: #555555;
    padding-bottom: 3px;
}

QTextEdit {
    border: 1px solid #DDDDDD;
    border-radius: 4px;
    padding: 8px;
    font-size: 13px;
    background-color: #FFFFFF;
}

QTextEdit:focus {
    border: 2px solid #4A90E2;
    background-color: #F8F9FA;
}

QPushButton {
    color: #FFFFFF;
    font-size: 14px;
    font-weight: bold;
    border: none;
    border-radius: 8px;
    padding: 12px 30px;
}

QPushButton#back_button {
    background-color: #000000;
}

QPushButton#back_button:hover {
    background-color: #333333;
}

QPushButton#next_button {
    background-color: #4A90E2;
}

QPushButton#next_button:hover {
    background-color: #357ABD;
}

QPushButton#pending_button {
    background-color: #FFA500;
}

QPushButton#pending_button:hover {
    background-color: #FF8C00;
}

QPushButton#instruction_button {
    background-color: #17a2b8;
}

QPushButton#instruction_button:hover {
    background-color: #138496;
}
"""
