import app_modern
import app_modern_v2
import reporting_export_v2

# Production wiring:
# - five-column engineering workbook exporter
# - modern maximized desktop shell
# - reliable latest-workbook opening
# - stronger secondary/action button visual hierarchy
app_modern.export_excel = reporting_export_v2.export_excel


if __name__ == "__main__":
    app_modern_v2.ProfessionalModernCPTApp().mainloop()
