import requests


def main():
    url = "http://localhost:8000/api/orders/place_order/"
    data = {
        "fundi_id": "00000000-0000-0000-0000-000000000000",
        "delivery_area": "Arusha CBD",
        "delivery_address_note": "Near the clock tower",
        "items": [
            {"product_id": "00000000-0000-0000-0000-000000000000", "quantity": 10}
        ],
    }

    response = requests.post(url, json=data, timeout=15)
    print(response.status_code)
    print(response.text)


if __name__ == "__main__":
    main()
