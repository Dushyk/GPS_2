import flet as ft


async def main(page: ft.Page):
    page.window.always_on_top = True
    page.on_error = lambda e: print(f"Page Error: {e.data}")
    page.scroll = ft.ScrollMode.ADAPTIVE
    page.appbar = ft.AppBar(title=ft.Text("Geolocator Tests"))
    gl = ft.Geolocator()
    page.overlay.append(gl)

    settings_dlg = lambda handler: ft.AlertDialog(
        adaptive=True,
        title=ft.Text("Opening Location Settings..."),
        content=ft.Text(
            "You are about to be redirected to the location/app settings. "
            "Please locate this app and grant it location permissions."
        ),
        actions=[
            ft.TextButton(
                text="OK",
                on_click=handler,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.CENTER,
    )

    def handle_permission_request(e):
        page.add(ft.Text(f"request_permission: {gl.request_permission()}"))

    def handle_get_permission_status(e):
        page.add(ft.Text(f"get_permission_status: {gl.get_permission_status()}"))

    def handle_get_current_position(e):
        p = gl.get_current_position()
        page.add(ft.Text(f"get_current_position: ({p.latitude}, {p.longitude})"))

    def handle_get_last_known_position(e):
        p = gl.get_last_known_position()
        page.add(ft.Text(f"get_last_known_position: ({p.latitude}, {p.longitude})"))

    def handle_location_service_enabled(e):
        page.add(
            ft.Text(f"is_location_service_enabled: {gl.is_location_service_enabled()}")
        )

    def handle_open_location_settings(e):
        page.close_dialog()
        page.add(ft.Text(f"open_location_settings: {gl.open_location_settings()}"))

    def handle_open_app_settings(e):
        page.close_dialog()
        page.add(ft.Text(f"open_app_settings: {gl.open_app_settings()}"))

    page.add(
        ft.Row(
            [
                ft.OutlinedButton(
                    "request_permission",
                    on_click=handle_permission_request,
                ),
                ft.OutlinedButton(
                    "get_permission_status",
                    on_click=handle_get_permission_status,
                ),
                ft.OutlinedButton(
                    "get_current_position",
                    on_click=handle_get_current_position,
                ),
                ft.OutlinedButton(
                    "get_last_known_position",
                    visible=False if page.web else True,
                    on_click=handle_get_last_known_position,
                ),
                ft.OutlinedButton(
                    "is_location_service_enabled",
                    on_click=handle_location_service_enabled,
                ),
                ft.OutlinedButton(
                    "open_location_settings",
                    visible=False if page.web else True,
                    on_click=lambda e: page.show_dialog(
                        settings_dlg(handle_open_location_settings)
                    ),
                ),
                ft.OutlinedButton(
                    "open_app_settings",
                    visible=False if page.web else True,
                    on_click=lambda e: page.show_dialog(
                        settings_dlg(handle_open_app_settings)
                    ),
                ),
            ],
            wrap=True,
        )
    )


ft.app(main)