import fitz  # PyMuPDF
import cv2
import numpy as np
import easyocr
import mysql.connector
import matplotlib.pyplot as plt
from tensorflow.keras.datasets import mnist
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Flatten
from tensorflow.keras.utils import to_categorical

# Загрузка и подготовка данных MNIST
(x_train, y_train), (x_test, y_test) = mnist.load_data()
x_train = x_train.reshape((x_train.shape[0], 28, 28, 1)).astype('float32') / 255
x_test = x_test.reshape((x_test.shape[0], 28, 28, 1)).astype('float32') / 255
y_train = to_categorical(y_train, 10)
y_test = to_categorical(y_test, 10)

# Построение модели
model = Sequential([
    Flatten(input_shape=(28, 28, 1)),
    Dense(128, activation='relu'),
    Dense(10, activation='softmax')
])

model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
model.fit(x_train, y_train, epochs=5, batch_size=32, validation_split=0.1)

# Пример функции для распознавания цифр
def recognize_digits(image):
    resized_image = cv2.resize(image, (28, 28))
    resized_image = resized_image.astype('float32') / 255
    resized_image = np.expand_dims(resized_image, axis=(0, -1))
    predictions = model.predict(resized_image)
    digit = np.argmax(predictions)
    return digit

# Функция для обнаружения и отрисовки печатей
def detect_and_draw_stamps(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blurred, 127, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    stamps_present = False
    for contour in contours:
        if cv2.contourArea(contour) > 1000:  # Фильтр для больших контуров
            x, y, w, h = cv2.boundingRect(contour)
            cv2.rectangle(image, (x, y), (x+w, y+h), (0, 0, 255), 2)
            stamps_present = True
    
    return stamps_present

# Database connection
db_connection = mysql.connector.connect(
    host="MySQL-5.7",
    user="root",
    password="",
    database="pdf_data"
)
cursor = db_connection.cursor()

# Список координат рамок
rectangles = [
    ((673, 27), (744, 54)), # номер документа
    ((661, 70), (956, 94)), # дата договора
    ((159, 96), (680, 114)), # первая сторона
    ((160, 186), (734, 204)), # вторая сторона
    ((478, 491), (799, 508)), # сумма
    ((157, 149), (944, 167)), # первые реквизиты
    ((154, 239), (949, 257))  # вторые реквизиты
]
tags = ["номер документа", "дата договора", "первая сторона", "вторая сторона", "сумма", "первые реквизиты", "вторые реквизиты"]

# Открываем PDF файл
pdf_path = r"C:\Users\Danila\R-Telecom\rework\model\images\img_2_with_stamp.pdf"
pdf_document = fitz.open(pdf_path)

# Инициализация списка для хранения извлеченных данных
extracted_data = [None] * len(tags)

# Обрабатываем первую страницу
if len(pdf_document) > 0:
    page = pdf_document.load_page(0)  # Загружаем первую страницу

    # Увеличиваем разрешение
    zoom = 3  # Масштабирование в 3 раза
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)

    # Преобразуем Pixmap в формат, поддерживаемый OpenCV
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n).copy()
    res_stamp = detect_and_draw_stamps(img)

    # Преобразуем изображение в формат BGR для OpenCV
    if pix.n == 4:  # RGBA
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGRA)
    else:  # RGB
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    # Применение гауссового размытия
    img = cv2.GaussianBlur(img, (5, 5), 0)

    # Применение адаптивного порогового преобразования
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    img = cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)

    # Улучшение резкости изображения
    kernel = np.array([[0, -1, 0],
                       [-1, 5, -1],
                       [0, -1, 0]])
    img = cv2.filter2D(img, -1, kernel)

    # Изменение размера изображения для удобного просмотра
    img_resized = cv2.resize(img, (1000, 1000))
    img = img_resized.copy()

    # Инициализация easyocr Reader
    reader = easyocr.Reader(['ru', 'en'])  # Используем русский и английский языки для распознавания

    # Отрисовка всех рамок с номерами и извлечение текста
    for i, (start, end) in enumerate(rectangles):
        cv2.rectangle(img, start, end, (0, 255, 0), 2)
        cv2.putText(img, f'#{i+1}', (start[0], start[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # Извлекаем текст из текущей рамки
        x1, y1 = start
        x2, y2 = end
        sub_img = img[y1:y2, x1:x2]

        # Распознаем текст с помощью easyocr
        result = reader.readtext(sub_img)

        # Проверяем, есть ли распознанный текст
        if result:
            if tags[i] == "сумма":
                # Очистка и форматирование текста суммы
                first_word = result[0][1].split(' ')[0] if result else None
                extracted_data[i] = first_word.strip().replace(',', '.')
            else:
                # Выводим весь результат
                extracted_data[i] = " ".join([res[1].strip() for res in result])
            print(f"Результаты распознавания для рамки тега: {tags[i]}: {extracted_data[i]}")
        else:
            extracted_data[i] = None
            print(f"Результаты распознавания для рамки тега: {tags[i]}: None")

    # Отображаем изображение с рамками
    print("Наличие печатей: ", res_stamp)

    # Отображаем изображение с использованием matplotlib
    plt.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    plt.axis('off')
    plt.show()

    # Debugging: print the extracted data and length
    print("Extracted data:", extracted_data)
    print("Length of extracted data:", len(extracted_data))

    # Insert data into database
    insert_query = """
    INSERT INTO extracted_data (document_number, contract_date, first_party, second_party, amount, first_details, second_details, stamps_present)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    cursor.execute(insert_query, (*extracted_data, res_stamp))
    db_connection.commit()

else:
    print("PDF файл не содержит страниц.")

# Close the database connection
cursor.close()
db_connection.close()
