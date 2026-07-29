def get_products():
    products = []
    if not os.path.exists(CSV_FILE):
        return products
        
    try:
        with open(CSV_FILE, mode="r", encoding="utf-8-sig", errors="ignore") as file:
            # Читаем обычным csv.reader вместо DictReader, чтобы работать с индексами колонок
            reader = csv.reader(file, delimiter=",")
            
            # Пропускаем самую первую строку с заголовками
            header = next(reader, None)
            
            for row in reader:
                # Если строка пустая или в ней мало колонок — пропускаем
                if not row or len(row) < 10:
                    continue
                
                # По твоему файлу: 
                # Название (колонка 7 -> индекс 6)
                # Цвет (колонка 4 -> индекс 3)
                # Размер (колонка 5 -> индекс 4)
                # Цена продажи (колонка 13 -> индекс 12)
                # Фото (колонка 51 -> индекс 50)
                
                try:
                    name = row[6] if len(row) > 6 else "Товар Victoria's Secret"
                    color = row[3] if len(row) > 3 else "-"
                    size = row[4] if len(row) > 4 else "-"
                    price = row[12] if len(row) > 12 else "0"
                    
                    # Ссылка на фото обычно находится в самом конце (51-я колонка)
                    photo = row[50] if len(row) > 50 else ""
                except IndexError:
                    continue

                if not name or str(name).isspace():
                    continue

                products.append({
                    "name": str(name).strip(),
                    "price": str(price).strip(),
                    "color": str(color).strip(),
                    "size": str(size).strip(),
                    "photo": str(photo).strip()
                })
    except Exception as e:
        print(f"Ошибка при чтении CSV: {e}")
        
    return products
