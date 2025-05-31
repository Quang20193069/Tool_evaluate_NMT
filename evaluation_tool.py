import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QMessageBox, QStatusBar, QProgressBar
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

KOREAN_FILE = "src.txt"
VIETNAMESE_FILE = "target.txt"
LOG_FILE = "result.log"

STYLESHEET = """
QWidget#main_window {
    background-color: #FFFFFF;
}

QLabel#title_label {
    font-size: 24px;
    font-weight: bold;
    color: #333333;
    padding-top: 20px;
    padding-bottom: 5px; /* Giảm padding dưới để gần progress bar hơn */
}

/* Style cho Progress Bar */
QProgressBar {
    border: 1px solid #DDDDDD;
    border-radius: 8px;
    text-align: center; /* Căn giữa chữ hiển thị (ví dụ: 50/100) */
    font-weight: bold;
    color: #333;
    height: 22px; /* Thêm chiều cao cố định */
    margin-bottom: 30px; /* Thêm khoảng cách bên dưới */
}
QProgressBar::chunk {
    background-color: #4CAF50; /* Màu xanh lá cây */
    border-radius: 8px;
}


QLabel#field_label {
    font-size: 14px;
    color: #555555;
    padding-bottom: 5px;
}

QTextEdit {
    border: 1px solid #DDDDDD;
    border-radius: 8px;
    padding: 10px;
    font-size: 18px;
    background-color: #FFFFFF;
}

QTextEdit:focus {
    border: 1px solid #4A90E2;
}

QPushButton#back_button {
    background-color: #000000;
    color: #FFFFFF;
    font-size: 14px;
    font-weight: bold;
    border: none;
    border-radius: 8px;
    padding: 12px 30px;
}

QPushButton#back_button:hover {
    background-color: #333333;
}

QPushButton#next_button {
    background-color: #4A90E2;
    color: #FFFFFF;
    font-size: 14px;
    font-weight: bold;
    border: none;
    border-radius: 8px;
    padding: 12px 30px;
}

QPushButton#next_button:hover {
    background-color: #357ABD;
}
"""

class EvaluationTool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.korean_sentences = []
        self.vietnamese_sentences_original = []
        self.evaluations_data = []
        self.current_index = 0
        self.is_loading_data = True

        self.initUI()
        self.load_all_data()
        self.is_loading_data = False
        self.display_current_pair()
        self.update_progress_bar() 

    def initUI(self):
        self.setWindowTitle("Tool Evaluate by NMT Teams")
        self.setGeometry(100, 100, 900, 800) 
        
        central_widget = QWidget(self)
        central_widget.setObjectName("main_window")
        self.setCentralWidget(central_widget)
        self.setStyleSheet(STYLESHEET)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(40, 0, 40, 0)

        title_label = QLabel("Tool Evaluate is developed by NMT Teams")
        title_label.setObjectName("title_label")
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        self.progress_bar = QProgressBar()
        main_layout.addWidget(self.progress_bar)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        
        source_label = QLabel("Source sentence")
        source_label.setObjectName("field_label")
        self.korean_text_display = QTextEdit()
        self.korean_text_display.setReadOnly(True)
        self.korean_text_display.setFixedHeight(80)
        content_layout.addWidget(source_label)
        content_layout.addWidget(self.korean_text_display)
        
        translate_label = QLabel("Translate sentence")
        translate_label.setObjectName("field_label")
        self.vietnamese_original_text_display = QTextEdit()
        self.vietnamese_original_text_display.setReadOnly(True)
        self.vietnamese_original_text_display.setFixedHeight(80)
        content_layout.addWidget(translate_label)
        content_layout.addWidget(self.vietnamese_original_text_display)
        
        edit_label = QLabel("Translate sentence edit")
        edit_label.setObjectName("field_label")
        self.vietnamese_updated_text_input = QTextEdit()
        self.vietnamese_updated_text_input.setFixedHeight(80)
        content_layout.addWidget(edit_label)
        content_layout.addWidget(self.vietnamese_updated_text_input)

        main_layout.addWidget(content_widget)
        main_layout.addStretch()

        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(0, 20, 0, 20)

        self.back_button = QPushButton("Back")
        self.back_button.setObjectName("back_button")
        self.back_button.setCursor(Qt.PointingHandCursor)
        self.back_button.clicked.connect(self.handle_back)

        self.next_button = QPushButton("Next")
        self.next_button.setObjectName("next_button")
        self.next_button.setCursor(Qt.PointingHandCursor)
        self.next_button.clicked.connect(self.handle_next)

        footer_layout.addWidget(self.back_button)
        footer_layout.addStretch()
        footer_layout.addWidget(self.next_button)

        main_layout.addLayout(footer_layout)

    def update_progress_bar(self):
        if not self.evaluations_data:
            self.progress_bar.setVisible(False) 
            return
        
        self.progress_bar.setVisible(True)
        total_sentences = len(self.evaluations_data)
        completed_sentences = sum(1 for entry in self.evaluations_data if entry['vietnamese_updated'] is not None)
        
        self.progress_bar.setMaximum(total_sentences)
        self.progress_bar.setValue(completed_sentences)
        self.progress_bar.setFormat(f"{completed_sentences} / {total_sentences}") 
    
    def load_all_data(self):
        try:
            with open(KOREAN_FILE, 'r', encoding='utf-8') as f_ko:
                self.korean_sentences = [line.strip() for line in f_ko if line.strip()]
            with open(VIETNAMESE_FILE, 'r', encoding='utf-8') as f_vi:
                self.vietnamese_sentences_original = [line.strip() for line in f_vi if line.strip()]
            if not self.korean_sentences or not self.vietnamese_sentences_original:
                QMessageBox.critical(self, "Lỗi File", "Một hoặc cả hai file input rỗng.")
                self.disable_ui_and_exit()
                return
            if len(self.korean_sentences) != len(self.vietnamese_sentences_original):
                QMessageBox.critical(self, "Lỗi File", f"Số dòng không khớp giữa file '{KOREAN_FILE}' ({len(self.korean_sentences)}) và '{VIETNAMESE_FILE}' ({len(self.vietnamese_sentences_original)}).")
                self.disable_ui_and_exit()
                return
            self.evaluations_data = [
                {
                    'korean': self.korean_sentences[i],
                    'vietnamese_original': self.vietnamese_sentences_original[i],
                    'vietnamese_updated': None
                } for i in range(len(self.korean_sentences))
            ]
            self.load_log_and_set_index()
        except FileNotFoundError as e:
            QMessageBox.critical(self, "Lỗi File", f"Không tìm thấy file: {e.filename}")
            self.disable_ui_and_exit()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi không xác định", f"Lỗi khi tải dữ liệu: {str(e)}")
            self.disable_ui_and_exit()

    def disable_ui_and_exit(self):
        self.next_button.setEnabled(False)
        self.back_button.setEnabled(False)
        self.vietnamese_updated_text_input.setEnabled(False)

    def load_log_and_set_index(self):
        max_logged_index = -1
        if os.path.exists(LOG_FILE):
            try:
                with open(LOG_FILE, 'r', encoding='utf-8') as f_log:
                    logged_items_in_current_files = 0
                    for line in f_log:
                        parts = line.strip().split('|', 2)
                        if len(parts) < 2: continue
                        log_ko = parts[0].strip()
                        log_vi_orig = parts[1].strip()
                        log_vi_upd = parts[2].strip() if len(parts) > 2 else ""
                        for i, entry in enumerate(self.evaluations_data):
                            if entry['korean'] == log_ko and entry['vietnamese_original'] == log_vi_orig:
                                entry['vietnamese_updated'] = log_vi_upd
                                max_logged_index = max(max_logged_index, i)
                                logged_items_in_current_files +=1
                                break
                    if logged_items_in_current_files > 0:
                        self.statusBar().showMessage(f"Đã tải {logged_items_in_current_files} mục từ {LOG_FILE}")
            except Exception as e:
                QMessageBox.warning(self, "Lỗi Đọc Log", f"Không thể đọc file log: {str(e)}")
        if max_logged_index != -1:
            self.current_index = max_logged_index + 1
            if self.current_index >= len(self.evaluations_data):
                self.current_index = len(self.evaluations_data)
        else:
            self.current_index = 0
        if len(self.evaluations_data) > 0:
            self.statusBar().showMessage(f"Sẵn sàng bắt đầu từ câu {self.current_index + 1 if self.current_index < len(self.evaluations_data) else self.current_index}/{len(self.evaluations_data)}")
        else:
            self.statusBar().showMessage("Không có dữ liệu để xử lý.")

    def display_current_pair(self):
        if self.is_loading_data: return
        total_pairs = len(self.evaluations_data)
        self.vietnamese_updated_text_input.setEnabled(self.current_index < total_pairs)
        if self.current_index >= total_pairs:
            QMessageBox.information(self, "Hoàn Tất", "Đã hoàn tất đánh giá! Quá OK, thank you")
            self.korean_text_display.clear()
            self.vietnamese_original_text_display.clear()
            self.vietnamese_updated_text_input.clear()
            self.next_button.setEnabled(False)
            return
        current_data = self.evaluations_data[self.current_index]
        self.korean_text_display.setText(current_data['korean'])
        self.vietnamese_original_text_display.setText(current_data['vietnamese_original'])
        self.vietnamese_updated_text_input.setText(current_data['vietnamese_updated'] if current_data['vietnamese_updated'] is not None else "")
        self.back_button.setEnabled(self.current_index > 0)
        self.next_button.setEnabled(True)
        self.vietnamese_updated_text_input.setFocus()

    def _save_current_input(self):
        if 0 <= self.current_index < len(self.evaluations_data):
            was_none = self.evaluations_data[self.current_index]['vietnamese_updated'] is None
            
            current_input = self.vietnamese_updated_text_input.toPlainText().strip()
            self.evaluations_data[self.current_index]['vietnamese_updated'] = current_input
            
            if was_none:
                self.update_progress_bar()

    def handle_next(self):
        self._save_current_input()
        if self.current_index < len(self.evaluations_data):
            self.current_index += 1
        self.display_current_pair()
        
    def handle_back(self):
        self._save_current_input()
        if self.current_index > 0:
            self.current_index -= 1
        self.display_current_pair()

    def save_log(self):
        try:
            with open(LOG_FILE, 'w', encoding='utf-8') as f_log:
                for entry in self.evaluations_data:
                    if entry['vietnamese_updated'] is not None:
                        log_line = f"{entry['korean']} | {entry['vietnamese_original']} | {entry['vietnamese_updated']}"
                        f_log.write(log_line + "\n")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi Lưu Log", f"Không thể lưu file log: {str(e)}")

    def closeEvent(self, event):
        self._save_current_input()
        reply = QMessageBox.question(self, 'Xác nhận đóng',
                                     "Bạn có chắc chắn muốn đóng và lưu kết quả?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.save_log()
            event.accept()
        else:
            event.ignore()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = EvaluationTool()
    ex.show()
    sys.exit(app.exec_())