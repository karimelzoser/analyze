import app_modern
import reporting_export_v2

# Keep the modern UI while using the five-column production workbook exporter.
app_modern.export_excel = reporting_export_v2.export_excel


if __name__ == "__main__":
    app_modern.ModernCPTApp().mainloop()
