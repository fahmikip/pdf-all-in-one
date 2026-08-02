"""Local application settings and dependency health."""
from pathlib import Path

from PySide6.QtWidgets import QApplication, QCheckBox, QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from app.config import ConfigStore, Settings, local_data_dir
from core.utils.history import HistoryStore
from core.utils.system_utils import dependency_status
from ui.themes.palette import stylesheet_for


class SettingsPage(QWidget):
    def __init__(self, settings: Settings, store: ConfigStore) -> None:
        super().__init__(); self.settings = settings; self.store = store; layout = QVBoxLayout(self); layout.setContentsMargins(36, 28, 36, 28)
        title = QLabel("Settings"); title.setObjectName("title"); layout.addWidget(title); form = QFormLayout()
        self.theme = QComboBox(); self.theme.addItems(["System", "Light", "Dark"]); self.theme.setCurrentText(settings.theme.title()); form.addRow("Theme", self.theme)
        self.output = QLabel(settings.default_output_folder or "Ask each time"); choose = QPushButton("Choose Folder"); choose.clicked.connect(self.choose_output); output_row = QHBoxLayout(); output_row.addWidget(self.output, 1); output_row.addWidget(choose); form.addRow("Default output", output_row)
        self.compression = QComboBox(); self.compression.addItems(["Low", "Recommended", "High", "Maximum"]); self.compression.setCurrentText(settings.default_compression.title()); form.addRow("Default compression", self.compression)
        self.dpi = QComboBox(); self.dpi.addItems(["72", "96", "150", "200", "300", "600"]); self.dpi.setCurrentText(str(settings.default_dpi)); form.addRow("Default DPI", self.dpi)
        self.update_checks = QCheckBox("Notify me when a new GitHub release is available"); self.update_checks.setChecked(settings.check_updates); form.addRow("Updates", self.update_checks)
        save = QPushButton("Save Settings"); save.setObjectName("primary"); save.clicked.connect(self.save); form.addRow(save); layout.addLayout(form)
        heading = QLabel("Dependencies"); heading.setObjectName("section"); layout.addWidget(heading); self.dependencies = QTableWidget(0, 2); self.dependencies.setHorizontalHeaderLabels(["Component", "Status / Location"]); self.dependencies.horizontalHeader().setStretchLastSection(True); layout.addWidget(self.dependencies)
        actions = QHBoxLayout(); refresh = QPushButton("Refresh Dependencies"); refresh.clicked.connect(self.refresh); clear_temp = QPushButton("Clear Temporary Files"); clear_temp.clicked.connect(self.clear_temp); clear_history = QPushButton("Clear History"); clear_history.clicked.connect(lambda: HistoryStore().clear())
        for button in (refresh, clear_temp, clear_history): actions.addWidget(button)
        actions.addStretch(); layout.addLayout(actions); self.refresh()

    def choose_output(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Default output folder", self.settings.default_output_folder)
        if folder: self.settings.default_output_folder = folder; self.output.setText(folder)
    def save(self) -> None:
        self.settings.theme = self.theme.currentText().lower(); self.settings.default_compression = self.compression.currentText().lower(); self.settings.default_dpi = int(self.dpi.currentText()); self.settings.check_updates = self.update_checks.isChecked(); self.store.save(self.settings)
        QApplication.instance().setStyleSheet(stylesheet_for(self.settings.theme)); QMessageBox.information(self, "Settings saved", "Your settings were saved locally.")
    def refresh(self) -> None:
        status = dependency_status(); self.dependencies.setRowCount(len(status))
        for row, (name, value) in enumerate(status.items()): self.dependencies.setItem(row, 0, QTableWidgetItem(name)); self.dependencies.setItem(row, 1, QTableWidgetItem(value))
        self.dependencies.resizeColumnsToContents()
    def clear_temp(self) -> None:
        folder = local_data_dir() / "temp"; count = 0
        if folder.exists():
            for path in folder.iterdir():
                if path.is_file(): path.unlink(missing_ok=True); count += 1
        QMessageBox.information(self, "Temporary files", f"Removed {count} temporary file(s).")
