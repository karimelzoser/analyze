import reporting_pdf_ref
import app_pro

# Final entry point: professional UI + complete Excel + reference-style PDFs.
app_pro.generate_pdf = reporting_pdf_ref.generate_pdf


class FinalCPTApp(app_pro.CPTApp):
    def refresh_chart(self):
        # Coordinate-map mode creates a colorbar axis. Remove auxiliary axes
        # before changing views so no stale colorbar remains after switching.
        if hasattr(self, "fig") and hasattr(self, "ax"):
            for extra_ax in list(self.fig.axes):
                if extra_ax is not self.ax:
                    self.fig.delaxes(extra_ax)
        return super().refresh_chart()


if __name__ == "__main__":
    FinalCPTApp().mainloop()
