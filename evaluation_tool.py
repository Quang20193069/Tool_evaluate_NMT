import sys
import os
import json
from typing import List, Dict, Optional

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QMessageBox, QStatusBar, QProgressBar,
    QComboBox, QCheckBox, QDialog, QListWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QKeyEvent

from ui_constants import UIConstants, STYLESHEET
from user import USERS 
from instruction import MAIN

class NavigableTextEdit(QTextEdit):
    enterPressed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Return and not event.modifiers():
            self.enterPressed.emit()
        else:
            super().keyPressEvent(event)


class DataManager:
    def __init__(self):
        self.src_sentences: List[str] = []
        self.tgt_sentences_original: List[str] = []
        self.evaluations_data: List[Dict] = []
        self.current_index: int = 0
        self.current_user: Optional[str] = None
        self.sentence_start_time: float = 0  # Thời điểm bắt đầu làm câu hiện tại
        
        self.user_files = {
            user: {
                "src": f"data/{user}_src.txt",
                "tgt": f"data/{user}_target.txt",
                "log": f"results/{user}_result.log"
            } for user in USERS
        }

    def load_all_data(self, user: str) -> tuple[bool, str]:
        """Load all data for a user and return success status and error message if any."""
        self.current_user = user
        if not user:
            self.clear_data()
            return True, ""

        try:
            user_files = self.user_files[user]
            with open(user_files["src"], 'r', encoding='utf-8') as f_src:
                self.src_sentences = [line.strip() for line in f_src if line.strip()]
            with open(user_files["tgt"], 'r', encoding='utf-8') as f_tgt:
                self.tgt_sentences_original = [line.strip() for line in f_tgt if line.strip()]

            if not self.src_sentences or not self.tgt_sentences_original:
                return False, "One or both input files are empty."

            if len(self.src_sentences) != len(self.tgt_sentences_original):
                return False, f"Line count mismatch: {user_files['src']} ({len(self.src_sentences)}) vs {user_files['tgt']} ({len(self.tgt_sentences_original)})"

            self.evaluations_data = [
                {
                    'src': self.src_sentences[i],
                    'tgt_original': self.tgt_sentences_original[i],
                    'tgt_updated': None,
                    'notes': '',
                    'pending': False
                } for i in range(len(self.src_sentences))
            ]

            success = self._load_log()
            if not success:
                return False, "Failed to load log file"

            return True, ""

        except FileNotFoundError as e:
            return False, f"File not found: {e.filename}"
        except Exception as e:
            return False, f"Error loading data: {str(e)}"

    def clear_data(self):
        """Clear all loaded data."""
        self.evaluations_data = []
        self.src_sentences = []
        self.tgt_sentences_original = []
        self.current_index = 0
        self.current_user = None

    def _load_log(self) -> bool:
        """Load and process log file, returns True if successful."""
        if not self.current_user:
            return False

        log_file = self.user_files[self.current_user]["log"]
        if not os.path.exists(log_file):
            return True  # No log file is not an error

        try:
            with open(log_file, 'r', encoding='utf-8') as f_log:
                try:
                    # Try JSON format first
                    log_data = json.load(f_log)
                    self._process_json_log(log_data)
                except json.JSONDecodeError:
                    # Fall back to legacy format
                    f_log.seek(0)
                    self._process_legacy_log(f_log)
            return True
        except Exception:
            return False

    def _process_json_log(self, log_data: List[Dict]):
        """Process JSON format log data."""
        for log_entry in log_data:
            for i, entry in enumerate(self.evaluations_data):
                if (entry['src'] == log_entry['src'] and 
                    entry['tgt_original'] == log_entry['tgt']):
                    entry['tgt_updated'] = log_entry['tgt_edit']
                    entry['notes'] = log_entry.get('notes', '')
                    entry['pending'] = log_entry.get('pending', False)
                    self.current_index = max(self.current_index, i + 1)
                    break

    def _process_legacy_log(self, f_log):
        """Process legacy format log data."""
        for line in f_log:
            parts = line.strip().split('|')
            if len(parts) < 2:
                continue
            
            log_src = parts[0].strip()
            log_tgt_orig = parts[1].strip()
            log_tgt_upd = parts[2].strip() if len(parts) > 2 else ""
            log_notes = parts[3].strip() if len(parts) > 3 else ""
            
            for i, entry in enumerate(self.evaluations_data):
                if (entry['src'] == log_src and 
                    entry['tgt_original'] == log_tgt_orig):
                    entry['tgt_updated'] = log_tgt_upd
                    entry['notes'] = log_notes
                    self.current_index = max(self.current_index, i + 1)
                    break

    def save_log(self) -> tuple[bool, str]:
        """Save current progress to log file."""
        if not self.current_user:
            return False, "No user selected"

        try:
            output_data = [
                {
                    "src": entry['src'],
                    "tgt": entry['tgt_original'],
                    "tgt_edit": entry['tgt_updated'],
                    "notes": entry.get('notes', ''),
                    "pending": entry.get('pending', False)
                }
                for entry in self.evaluations_data
                if entry['tgt_updated'] is not None
            ]
            
            log_file = self.user_files[self.current_user]["log"]
            with open(log_file, 'w', encoding='utf-8') as f_log:
                json.dump(output_data, f_log, ensure_ascii=False, indent=2)
            return True, ""
        except Exception as e:
            return False, str(e)

    def get_current_data(self) -> Optional[Dict]:
        """Get the current sentence pair data."""
        if not self.evaluations_data:
            return None
        
        if self.current_index >= len(self.evaluations_data):
            self.current_index = len(self.evaluations_data) - 1
            
        return self.evaluations_data[self.current_index]

    def move_next(self) -> bool:
        """Move to next sentence pair if possible."""
        if self.current_index < len(self.evaluations_data) - 1:
            self.current_index += 1
            return True
        return False

    def move_back(self) -> bool:
        """Move to previous sentence pair if possible."""
        if self.current_index > 0:
            self.current_index -= 1
            return True
        return False

    def update_current_entry(self, tgt_updated: str, notes: str, pending: bool) -> bool:
        """Update the current entry with new data.
        
        Returns:
            bool: True nếu trạng thái đã xử lý của câu thay đổi, False nếu không
        """
        if 0 <= self.current_index < len(self.evaluations_data):
            entry = self.evaluations_data[self.current_index]
            
            # Kiểm tra trạng thái cũ
            old_completed = bool(
                (entry.get('tgt_updated') and entry['tgt_updated'].strip()) or 
                entry.get('pending', False)
            )
            
            # Cập nhật dữ liệu
            entry['tgt_updated'] = tgt_updated.strip()
            entry['notes'] = notes.strip()
            entry['pending'] = pending
            
            # Kiểm tra trạng thái mới
            new_completed = bool(
                (entry['tgt_updated'] and entry['tgt_updated'].strip()) or 
                entry['pending']
            )
            
            # Trả về True nếu trạng thái đã xử lý thay đổi
            return new_completed != old_completed
            
        return False

    def get_pending_cases(self) -> List[tuple[int, Dict]]:
        """Get all pending cases."""
        return [(i, data) for i, data in enumerate(self.evaluations_data) 
                if data.get('pending', False)]

    def is_current_sentence_completed(self) -> bool:
        """Kiểm tra xem câu hiện tại đã hoàn thành chưa.
        Một câu được coi là hoàn thành khi:
        - Có nội dung trong tgt_updated, HOẶC
        - Được đánh dấu là pending
        """
        if not self.evaluations_data or self.current_index >= len(self.evaluations_data):
            return False
            
        current = self.evaluations_data[self.current_index]
        return bool(
            (current.get('tgt_updated') and current['tgt_updated'].strip()) or 
            current.get('pending', False)
        )

    def get_current_work_time(self) -> float:
        """Lấy thời gian đã làm việc trên câu hiện tại (tính bằng giây)."""
        import time
        return time.time() - self.sentence_start_time

    def get_progress(self) -> tuple[int, int]:
        """Get progress as (completed, total).
        Returns:
            tuple[int, int]: (số câu đã xử lý, tổng số câu)
        Một câu được tính là đã xử lý khi:
        - Có nội dung dịch không rỗng, HOẶC
        - Được đánh dấu là pending
        """
        if not self.evaluations_data:
            return 0, 0
            
        total = len(self.evaluations_data)
        completed = sum(
            1 for entry in self.evaluations_data 
            if (entry.get('tgt_updated') and entry['tgt_updated'].strip()) or 
               entry.get('pending', False)
        )
        return completed, total

class EvaluationTool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.data_manager = DataManager()
        self.initUI()
        self.display_current_pair()
        self.update_progress_bar()

    def initUI(self):
        # Window setup
        self.setWindowTitle("Tool Evaluate by NMT Teams")
        self.setGeometry(100, 100, 1000, 700)  # Reduced window size
        self.setMinimumSize(800, 600)  # Reduced minimum size
        
        central_widget = QWidget(self)
        central_widget.setObjectName("main_window")
        self.setCentralWidget(central_widget)
        self.setStyleSheet(STYLESHEET)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(30, 20, 30, 20)  # Reduced margins
        main_layout.setSpacing(15)  # Reduced spacing

        # Title
        title_label = QLabel("Tool Evaluate is developed by NMT Teams")
        title_label.setObjectName("title_label")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 10px;")
        main_layout.addWidget(title_label)

        # User selection
        user_selection_layout = QHBoxLayout()
        user_label = QLabel("Select User:")
        user_label.setObjectName("field_label")
        user_label.setStyleSheet("font-size: 12px; font-weight: bold;")
        self.user_combobox = QComboBox()
        self.user_combobox.setFixedHeight(25)  # Reduced height
        self.user_combobox.setStyleSheet("font-size: 11px; padding: 2px 6px;")
        self.user_combobox.addItem("")
        self.user_combobox.addItems(self.data_manager.user_files.keys())
        self.user_combobox.setCurrentText("")
        self.user_combobox.currentTextChanged.connect(self.handle_user_change)

        user_selection_layout.addWidget(user_label)
        user_selection_layout.addWidget(self.user_combobox)
        main_layout.addLayout(user_selection_layout)

        # Content widget
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(8)  # Reduced spacing

        # Source text
        source_label = QLabel("Source sentence")
        source_label.setObjectName("field_label")
        source_label.setStyleSheet("font-size: 12px; font-weight: bold;")
        self.src_text_display = QTextEdit()
        self.src_text_display.setReadOnly(True)
        self.src_text_display.setFixedHeight(60)  # Reduced height
        self.src_text_display.setStyleSheet("font-size: 12px; padding: 6px;")
        content_layout.addWidget(source_label)
        content_layout.addWidget(self.src_text_display)

        # Target text
        translate_label = QLabel("Translate sentence")
        translate_label.setObjectName("field_label")
        translate_label.setStyleSheet("font-size: 12px; font-weight: bold;")
        self.tgt_original_text_display = QTextEdit()
        self.tgt_original_text_display.setReadOnly(True)
        self.tgt_original_text_display.setFixedHeight(60)  # Reduced height
        self.tgt_original_text_display.setStyleSheet("font-size: 12px; padding: 6px;")
        content_layout.addWidget(translate_label)
        content_layout.addWidget(self.tgt_original_text_display)

        # Edit text
        edit_label = QLabel("Translate sentence edit")
        edit_label.setObjectName("field_label")
        edit_label.setStyleSheet("font-size: 12px; font-weight: bold;")
        self.tgt_updated_text_input = NavigableTextEdit()
        self.tgt_updated_text_input.setFixedHeight(60)  # Reduced height
        self.tgt_updated_text_input.setStyleSheet("font-size: 12px; padding: 6px;")
        self.tgt_updated_text_input.enterPressed.connect(self.focus_notes)
        content_layout.addWidget(edit_label)
        content_layout.addWidget(self.tgt_updated_text_input)

        # Notes
        notes_label = QLabel("Notes")
        notes_label.setObjectName("field_label")
        notes_label.setStyleSheet("font-size: 12px; font-weight: bold;")
        self.notes_text_input = NavigableTextEdit()
        self.notes_text_input.setFixedHeight(60)  # Reduced height
        self.notes_text_input.setStyleSheet("font-size: 12px; padding: 6px;")
        self.notes_text_input.enterPressed.connect(self.trigger_next)
        content_layout.addWidget(notes_label)
        content_layout.addWidget(self.notes_text_input)

        # Pending checkbox
        self.pending_checkbox = QCheckBox("Mark as Pending")
        self.pending_checkbox.setStyleSheet("font-size: 12px;")
        content_layout.addWidget(self.pending_checkbox)

        main_layout.addWidget(content_widget)
        main_layout.addStretch()

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                height: 16px;
                font-size: 11px;
                text-align: center;
                margin-top: 8px;
                margin-bottom: 8px;
            }
        """)

        # Footer layout
        footer_layout = QVBoxLayout()
        footer_layout.setContentsMargins(0, 0, 0, 15)
        footer_layout.setSpacing(10)

        # Button layout
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)

        button_style = """
            QPushButton {
                font-size: 12px;
                padding: 6px 20px;
                border-radius: 4px;
            }
        """

        self.back_button = QPushButton("Back")
        self.back_button.setObjectName("back_button")
        self.back_button.setCursor(Qt.PointingHandCursor)
        self.back_button.clicked.connect(self.handle_back)

        # Instruction button
        self.instruction_button = QPushButton("Instruction")
        self.instruction_button.setObjectName("instruction_button")
        self.instruction_button.setCursor(Qt.PointingHandCursor)
        self.instruction_button.clicked.connect(self.show_instruction)
        # Add inline style to ensure visibility
        self.instruction_button.setStyleSheet("background-color: #17a2b8; color: white; font-size: 12px; padding: 6px 20px; border-radius: 4px;")

        self.pending_button = QPushButton("Pending Cases")
        self.pending_button.setObjectName("pending_button")
        self.pending_button.setCursor(Qt.PointingHandCursor)
        self.pending_button.setStyleSheet(button_style)
        self.pending_button.clicked.connect(self.show_pending_cases)

        self.next_button = QPushButton("Next")
        self.next_button.setObjectName("next_button")
        self.next_button.setCursor(Qt.PointingHandCursor)
        self.next_button.setStyleSheet(button_style)
        self.next_button.clicked.connect(self.handle_next)

        # Update button layout
        button_layout.addWidget(self.back_button)
        button_layout.addStretch()
        button_layout.addWidget(self.instruction_button)
        button_layout.addStretch()
        button_layout.addWidget(self.pending_button)
        button_layout.addStretch()
        button_layout.addWidget(self.next_button)

        footer_layout.addLayout(button_layout)
        footer_layout.addWidget(self.progress_bar)

        main_layout.addLayout(footer_layout)
        
        # Status bar with smaller font
        self.statusBar().setStyleSheet("font-size: 11px;")
        
    def handle_user_change(self, user: str):
        success, error_message = self.data_manager.load_all_data(user)
        if not success:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("Error Loading Data")
            msg.setText(error_message)
            msg.setStyleSheet("""
                QMessageBox {
                    background-color: white;
                }
                QLabel {
                    font-size: 12px;
                    color: #dc3545;
                    padding: 10px;
                }
                QPushButton {
                    padding: 6px 20px;
                    border-radius: 4px;
                    font-size: 12px;
                    background-color: #dc3545;
                    color: white;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #c82333;
                }
            """)
            msg.exec_()
            self.disable_ui_and_exit()
            return

        self.display_current_pair()
        self.update_progress_bar()

    def update_progress_bar(self):
        completed, total = self.data_manager.get_progress()
        if total == 0:
            self.progress_bar.setVisible(False)
            return

        self.progress_bar.setVisible(True)
        progress_percentage = int((completed / total) * 100)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(progress_percentage)
        self.progress_bar.setFormat(f"{progress_percentage}%")

    def disable_ui_and_exit(self):
        self.next_button.setEnabled(False)
        self.back_button.setEnabled(False)
        self.tgt_updated_text_input.setEnabled(False)

    def display_current_pair(self):
        import time
        self.data_manager.sentence_start_time = time.time()  # Reset timer
        
        current_data = self.data_manager.get_current_data()
        if current_data is None:
            self.src_text_display.setText("")
            self.tgt_original_text_display.setText("")
            self.tgt_updated_text_input.setText("")
            self.notes_text_input.setText("")
            self.pending_checkbox.setChecked(False)
            self.back_button.setEnabled(False)
            self.next_button.setEnabled(False)
            self.progress_bar.setVisible(False)
            return

        self.tgt_updated_text_input.setEnabled(True)
        self.src_text_display.setText(current_data['src'])
        self.tgt_original_text_display.setText(current_data['tgt_original'])
        self.tgt_updated_text_input.setText(current_data['tgt_updated'] or "")
        self.notes_text_input.setText(current_data.get('notes', ''))
        self.pending_checkbox.setChecked(current_data.get('pending', False))

        self.back_button.setEnabled(self.data_manager.current_index > 0)
        self.next_button.setEnabled(True)
        self.tgt_updated_text_input.setFocus()
        self.update_sentence_counter()

    def _save_current_input(self):
        """Lưu thay đổi của câu hiện tại."""
        changed = self.data_manager.update_current_entry(
            self.tgt_updated_text_input.toPlainText(),
            self.notes_text_input.toPlainText(),
            self.pending_checkbox.isChecked()
        )
        if changed:
            self.update_progress_bar()

    def handle_next(self):
        # Kiểm tra thời gian làm việc
        MINIMUM_TIME = 5.0  # Thời gian tối thiểu (giây)
        work_time = self.data_manager.get_current_work_time()
        
        if not self.data_manager.is_current_sentence_completed() and work_time < MINIMUM_TIME:
            remaining = int(MINIMUM_TIME - work_time)
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("Warning")
            msg.setText(f"Bạn đang làm quá nhanh!\nVui lòng dành ít nhất {remaining} giây nữa để xem xét câu này.")
            msg.setStyleSheet("""
                QMessageBox {
                    background-color: white;
                }
                QLabel {
                    font-size: 12px;
                    color: #856404;
                    padding: 10px;
                }
                QPushButton {
                    padding: 6px 20px;
                    border-radius: 4px;
                    font-size: 12px;
                    background-color: #ffc107;
                    color: #333;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #e0a800;
                }
            """)
            msg.exec_()
            return
            
        self._save_current_input()
        success, error_message = self.data_manager.save_log()

        if not success:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("Error Saving Log")
            msg.setText(error_message)
            msg.setStyleSheet("""
                QMessageBox {
                    background-color: white;
                }
                QLabel {
                    font-size: 12px;
                    color: #dc3545;
                    padding: 10px;
                }
                QPushButton {
                    padding: 6px 20px;
                    border-radius: 4px;
                    font-size: 12px;
                    background-color: #dc3545;
                    color: white;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #c82333;
                }
            """)
            msg.exec_()
            return

        if self.data_manager.move_next():
            self.display_current_pair()
        else:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("Complete")
            msg.setText("Thank you for completing the task!")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.setStyleSheet("""
                QMessageBox {
                    background-color: white;
                }
                QLabel {
                    font-size: 12px;
                    color: #333;
                    padding: 10px;
                }
                QPushButton {
                    padding: 6px 20px;
                    border-radius: 4px;
                    font-size: 12px;
                    background-color: #28a745;
                    color: white;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #218838;
                }
            """)
            msg.exec_()
            self.display_current_pair()

    def handle_back(self):
        self._save_current_input()
        if self.data_manager.move_back():
            self.display_current_pair()

    def update_sentence_counter(self):
        """Update the sentence counter display in the status bar."""
        completed, total = self.data_manager.get_progress()
        current = self.data_manager.current_index + 1
        self.statusBar().showMessage(f"Current sentence: {current}/{total}")

    def closeEvent(self, event):
        self._save_current_input()
        
        # Create custom close confirmation dialog
        dialog = QDialog(self)
        dialog.setWindowTitle('Confirm Close')
        dialog.setFixedWidth(400)
        dialog.setStyleSheet("""
            QDialog {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 8px;
            }
            QPushButton {
                padding: 8px 24px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton#yes_button {
                background-color: #dc3545;
                color: white;
                border: none;
            }
            QPushButton#yes_button:hover {
                background-color: #c82333;
            }
            QPushButton#no_button {
                background-color: #f8f9fa;
                color: #212529;
                border: 1px solid #dee2e6;
            }
            QPushButton#no_button:hover {
                background-color: #e2e6ea;
                border-color: #dae0e5;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(24, 24, 24, 24)

        # Message label
        msg_label = QLabel("Are you sure you want to close?")
        msg_label.setStyleSheet("font-size: 15px; color: #212529;")
        msg_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(msg_label)

        # Buttons layout
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)

        no_button = QPushButton("Cancel")
        no_button.setObjectName("no_button")
        no_button.setCursor(Qt.PointingHandCursor)
        no_button.clicked.connect(dialog.reject)

        yes_button = QPushButton("Close")
        yes_button.setObjectName("yes_button")
        yes_button.setCursor(Qt.PointingHandCursor)
        yes_button.clicked.connect(dialog.accept)

        button_layout.addWidget(no_button)
        button_layout.addWidget(yes_button)

        layout.addLayout(button_layout)
        dialog.setLayout(layout)

        reply = dialog.exec_()
        
        if reply == QDialog.Accepted:
            event.accept()
        else:
            event.ignore()

    def show_pending_cases(self):
        pending_cases = self.data_manager.get_pending_cases()
        if not pending_cases:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("Pending Cases")
            msg.setText("No pending cases found.")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.setStyleSheet("""
                QMessageBox {
                    background-color: white;
                }
                QPushButton {
                    padding: 6px 20px;
                    border-radius: 4px;
                    font-size: 12px;
                    background-color: #007bff;
                    color: white;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #0056b3;
                }
            """)
            msg.exec_()
            return
            
        dialog = QDialog(self)
        dialog.setWindowTitle("Pending Cases")
        dialog.setFixedWidth(350)
        dialog.setStyleSheet("""
            QDialog {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 6px;
            }
            QLabel {
                font-size: 12px;
                color: #444;
                padding: 5px;
            }
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 12px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
            }
            QListWidget::item:hover {
                background-color: #f5f5f5;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Add header label
        header = QLabel(f"Found {len(pending_cases)} pending cases:")
        header.setStyleSheet("font-weight: bold; color: #333;")
        layout.addWidget(header)
        
        # Add list widget
        list_widget = QListWidget()
        for index, data in pending_cases:
            item = QListWidgetItem(f"Case #{index + 1}: {data['src'][:30]}...")
            item.setData(Qt.UserRole, index)
            list_widget.addItem(item)
        
        list_widget.setFixedHeight(min(200, len(pending_cases) * 35 + 20))
        layout.addWidget(list_widget)
        
        # Add instruction label
        instruction = QLabel("Click on a case to navigate to it")
        instruction.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(instruction)
        
        dialog.setLayout(layout)
        
        def on_item_selected(item):
            self.data_manager.current_index = item.data(Qt.UserRole)
            self.display_current_pair()
            dialog.close()
            
        list_widget.itemClicked.connect(on_item_selected)
        dialog.exec_()

    def focus_notes(self):
        """Handle Enter key in target edit - focus notes field"""
        self.notes_text_input.setFocus()

    def trigger_next(self):
        """Handle Enter key in notes - trigger next button if validation passes"""
        # Check minimum time requirement
        if not self.data_manager.is_current_sentence_completed():
            work_time = self.data_manager.get_current_work_time()
            MINIMUM_TIME = 5.0
            
            if work_time < MINIMUM_TIME:
                remaining = int(MINIMUM_TIME - work_time)
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Warning)
                msg.setWindowTitle("Warning")
                msg.setText(f"Bạn đang làm quá nhanh!\nVui lòng dành ít nhất {remaining} giây nữa để xem xét câu này.")
                msg.setStyleSheet("""
                    QMessageBox {
                        background-color: white;
                    }
                    QLabel {
                        font-size: 12px;
                        color: #856404;
                        padding: 10px;
                    }
                    QPushButton {
                        padding: 6px 20px;
                        border-radius: 4px;
                        font-size: 12px;
                        background-color: #ffc107;
                        color: #333;
                        border: none;
                    }
                    QPushButton:hover {
                        background-color: #e0a800;
                    }
                """)
                msg.exec_()
                return
                
        self.handle_next()

    def closeEvent(self, event):
        self._save_current_input()
        
        # Create custom close confirmation dialog
        dialog = QDialog(self)
        dialog.setWindowTitle('Confirm Close')
        dialog.setFixedWidth(400)
        dialog.setStyleSheet("""
            QDialog {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 8px;
            }
            QPushButton {
                padding: 8px 24px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton#yes_button {
                background-color: #dc3545;
                color: white;
                border: none;
            }
            QPushButton#yes_button:hover {
                background-color: #c82333;
            }
            QPushButton#no_button {
                background-color: #f8f9fa;
                color: #212529;
                border: 1px solid #dee2e6;
            }
            QPushButton#no_button:hover {
                background-color: #e2e6ea;
                border-color: #dae0e5;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(24, 24, 24, 24)

        # Message label
        msg_label = QLabel("Are you sure you want to close?")
        msg_label.setStyleSheet("font-size: 15px; color: #212529;")
        msg_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(msg_label)

        # Buttons layout
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)

        no_button = QPushButton("Cancel")
        no_button.setObjectName("no_button")
        no_button.setCursor(Qt.PointingHandCursor)
        no_button.clicked.connect(dialog.reject)

        yes_button = QPushButton("Close")
        yes_button.setObjectName("yes_button")
        yes_button.setCursor(Qt.PointingHandCursor)
        yes_button.clicked.connect(dialog.accept)

        button_layout.addWidget(no_button)
        button_layout.addWidget(yes_button)

        layout.addLayout(button_layout)
        dialog.setLayout(layout)

        reply = dialog.exec_()
        
        if reply == QDialog.Accepted:
            event.accept()
        else:
            event.ignore()

    def show_pending_cases(self):
        pending_cases = self.data_manager.get_pending_cases()
        if not pending_cases:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("Pending Cases")
            msg.setText("No pending cases found.")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.setStyleSheet("""
                QMessageBox {
                    background-color: white;
                }
                QPushButton {
                    padding: 6px 20px;
                    border-radius: 4px;
                    font-size: 12px;
                    background-color: #007bff;
                    color: white;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #0056b3;
                }
            """)
            msg.exec_()
            return
            
        dialog = QDialog(self)
        dialog.setWindowTitle("Pending Cases")
        dialog.setFixedWidth(350)
        dialog.setStyleSheet("""
            QDialog {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 6px;
            }
            QLabel {
                font-size: 12px;
                color: #444;
                padding: 5px;
            }
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 12px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
            }
            QListWidget::item:hover {
                background-color: #f5f5f5;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Add header label
        header = QLabel(f"Found {len(pending_cases)} pending cases:")
        header.setStyleSheet("font-weight: bold; color: #333;")
        layout.addWidget(header)
        
        # Add list widget
        list_widget = QListWidget()
        for index, data in pending_cases:
            item = QListWidgetItem(f"Case #{index + 1}: {data['src'][:30]}...")
            item.setData(Qt.UserRole, index)
            list_widget.addItem(item)
        
        list_widget.setFixedHeight(min(200, len(pending_cases) * 35 + 20))
        layout.addWidget(list_widget)
        
        # Add instruction label
        instruction = QLabel("Click on a case to navigate to it")
        instruction.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(instruction)
        
        dialog.setLayout(layout)
        
        def on_item_selected(item):
            self.data_manager.current_index = item.data(Qt.UserRole)
            self.display_current_pair()
            dialog.close()
            
        list_widget.itemClicked.connect(on_item_selected)
        dialog.exec_()

    def show_instruction(self):
        """Show instruction dialog."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Instruction")
        dialog.setFixedWidth(500)
        dialog.setStyleSheet("""
            QDialog {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 8px;
            }
            QLabel {
                font-size: 12px;
                color: #444;
                padding: 10px;
            }
            QPushButton {
                padding: 8px 24px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton#close_button {
                background-color: #007bff;
                color: white;
                border: none;
            }
            QPushButton#close_button:hover {
                background-color: #0056b3;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(24, 24, 24, 24)

        # Instruction label
        instruction_label = QLabel(MAIN)
        instruction_label.setWordWrap(True)
        layout.addWidget(instruction_label)

        # Close button
        close_button = QPushButton("Close")
        close_button.setObjectName("close_button")
        close_button.setCursor(Qt.PointingHandCursor)
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button, alignment=Qt.AlignCenter)

        dialog.setLayout(layout)
        dialog.exec_()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = EvaluationTool()
    ex.show()
    sys.exit(app.exec_())