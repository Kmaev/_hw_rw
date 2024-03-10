import dataclasses
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import os


@dataclasses.dataclass
class upload_gd:

    gd_folder_name: str
    file_name: str
    local_folder_path: str

    def upload(self):
        """upload files to drive
        Args:
        Returns:
        """
        gauth = GoogleAuth()
        script_directory = os.path.dirname(os.path.abspath(__file__))
        client_secrets_path = os.path.join(script_directory, "client_secrets.json")

        gauth.DEFAULT_SETTINGS["client_config_file"] = client_secrets_path

        if gauth.credentials is None:
            gauth.LoadCredentialsFile("mycreds.txt")
            gauth.LocalWebserverAuth()
        elif gauth.access_token_expired:
            gauth.Refresh()
        else:
            gauth.Autorize()

        gauth.SaveCredentialsFile("mycreds.txt")

        drive = GoogleDrive(gauth)

        folder_query = f"title = '{self.gd_folder_name}' and mimeType = 'application/vnd.google-apps.folder'"
        folder_list = drive.ListFile({"q": folder_query}).GetList()
        folder_id = folder_list[0]["id"]

        mime_type = "application/octet-stream"
        file = drive.CreateFile({"parents": [{"id": folder_id}], "title": self.file_name})
        file.SetContentFile("{}/{}".format(self.local_folder_path, self.file_name))
        file.Upload()
