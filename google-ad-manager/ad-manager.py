# Najprostszy "hello world" dla Ad Manager API — sprawdza, czy uwierzytelnienie
# działa, wypisując kod i nazwę sieci, do której podpięty jest klucz.
from googleads import ad_manager


def main(client):
  # Initialize appropriate service.
  network_service = client.GetService('NetworkService', version='v202402')

  current_network = network_service.getCurrentNetwork()

  print("Current network has network code '%s' and display name '%s'." %
        (current_network['networkCode'], current_network['displayName']))


if __name__ == '__main__':
  # LoadFromStorage() bez argumentu szuka pliku googleads.yaml w katalogu domowym
  # (patrz README w tym folderze) — podaj ścieżkę jawnie tylko jeśli trzymasz go gdzie indziej.
  ad_manager_client = ad_manager.AdManagerClient.LoadFromStorage()

  main(ad_manager_client)
