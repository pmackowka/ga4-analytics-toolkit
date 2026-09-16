// Pobierz nazwę promocji z warstw danych GTM, prawdopodobnie z obiektu eventModel
var promotionName = {{DLV - eventModel.promotion_name}};
// Pobierz ID promocji z warstw danych GTM, prawdopodobnie z obiektu eventModel
var promotionId = {{DLV - eventModel.promotion_id}};
// Pobierz aktualną wartość 'promotion_name' z pamięci sesji, jeśli istnieje
var cookiePromotionName = sessionStorage.getItem("promotion_name");
// Pobierz nazwę zdarzenia z GTM i usuń końcówkę "_promotion", np. z "view_promotion" robi "view"
var event = {{Event}};
event = event.replace("_promotion", "");

// Sprawdź, czy 'promotion_name' w pamięci sesji jest puste (null) lub zawiera "_view"
// Jeśli tak, zaktualizuj pamięć sesji nazwą promocji i typem interakcji
if(cookiePromotionName === null || cookiePromotionName.includes("_view")){

    // Ustaw 'promotion_name' w pamięci sesji, łącząc nazwę promocji z typem interakcji, np. "Promocja_view"
    sessionStorage.setItem("promotion_name", promotionName + "_" + event);
    // Ustaw 'promotion_id' w pamięci sesji, zapisując ID aktualnej promocji
    sessionStorage.setItem("promotion_id", promotionId);

}

// Jeśli zdarzenie to "select", zaktualizuj pamięć sesji niezależnie od poprzedniego stanu
if(event === "select"){

    // Ustaw 'promotion_name' w pamięci sesji, łącząc nazwę promocji z "select", np. "Promocja_select"
    sessionStorage.setItem("promotion_name", promotionName + "_" + event);
    // Ustaw 'promotion_id' w pamięci sesji, zapisując ID aktualnej promocji
    sessionStorage.setItem("promotion_id", promotionId);

}