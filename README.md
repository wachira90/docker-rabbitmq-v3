# docker rabbitmq v3

การติดตั้ง **RabbitMQ ด้วย Docker** และโค้ด **Python** สำหรับจำลองระบบ **Submit Order** (ส่งคำสั่งซื้อ) ครับ

เราจะแบ่งเป็น 3 ส่วน:

1.  **Run RabbitMQ** บน Docker
2.  **Publisher (คนส่ง)**: โค้ด Python สำหรับสร้าง Order
3.  **Consumer (คนรับ)**: โค้ด Python สำหรับรับ Order ไปประมวลผล (เพื่อให้เห็นภาพครบวงจร)

-----

### 1\. ติดตั้งและรัน RabbitMQ ด้วย Docker

ใช้คำสั่งนี้เพื่อรัน RabbitMQ พร้อมหน้าจัดการ (Management UI):

```bash
docker run -d --hostname my-rabbit --name rabbitmq-server \
  -p 5672:5672 -p 15672:15672 \
  rabbitmq:3-management
```

  * **Port 5672**: สำหรับส่งข้อความ (Python จะต่อเข้าพอร์ตนี้)
  * **Port 15672**: สำหรับหน้าเว็บ Management (เข้าผ่าน `http://localhost:15672` login: `guest`/`guest`)

-----

### 2\. เตรียม Environment ภาษา Python

ติดตั้ง Library `pika` ที่เป็น client ยอดนิยมสำหรับ RabbitMQ:

```bash
pip install pika
```

-----

### 3\. โค้ดส่วนส่งคำสั่งซื้อ (`producer.py`)

โค้ดนี้จะจำลองการรับ Order จากลูกค้า แล้วแปลงเป็น JSON ส่งเข้าคิวครับ

```python
import pika
import json
import uuid

# 1. เชื่อมต่อกับ RabbitMQ Server
connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='localhost', port=5672)
)
channel = connection.channel()

# 2. สร้าง Queue ชื่อ 'order_queue' (ถ้ามีอยู่แล้วมันจะไม่สร้างซ้ำ)
# durable=True คือถ้า RabbitMQ ดับ คิวจะไม่หาย
channel.queue_declare(queue='order_queue', durable=True)

def submit_order(product_name, quantity, price):
    # จำลองข้อมูล Order เป็น Dictionary
    order_data = {
        'order_id': str(uuid.uuid4()),
        'product': product_name,
        'quantity': quantity,
        'total_price': price * quantity,
        'status': 'pending'
    }

    # แปลงข้อมูลเป็น JSON String
    message = json.dumps(order_data)

    # 3. ส่งข้อมูลเข้า Exchange (Default Exchange ใช้ค่าว่าง '')
    channel.basic_publish(
        exchange='',
        routing_key='order_queue',
        body=message,
        properties=pika.BasicProperties(
            delivery_mode=2,  # ทำให้ข้อความคงอยู่ (Persistent) แม้ RabbitMQ restart
        )
    )
    print(f" [x] Sent Order: {order_data['order_id']}")

# --- ทดลองส่ง Order ---
if __name__ == '__main__':
    submit_order("iPhone 15", 1, 32000)
    submit_order("AirPods Pro", 2, 8900)
    submit_order("MacBook Air", 1, 45000)

    # ปิดการเชื่อมต่อ
    connection.close()
```

-----

### 4\. โค้ดส่วนรับคำสั่งซื้อไปทำต่อ (`consumer.py`)

ระบบจะไม่สมบูรณ์ถ้าไม่มีคนเอา Order ไปทำต่อ (เช่น ตัดสต็อก, บันทึกลง Database) นี่คือโค้ดฝั่งรับครับ:

```python
import pika
import json
import time

# 1. เชื่อมต่อกับ RabbitMQ (เหมือนเดิม)
connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='localhost', port=5672)
)
channel = connection.channel()

# ประกาศ Queue อีกครั้งเพื่อให้มั่นใจว่ามี Queue นี้อยู่จริง (เผื่อรัน consumer ก่อน producer)
channel.queue_declare(queue='order_queue', durable=True)

print(' [*] Waiting for orders. To exit press CTRL+C')

# ฟังก์ชัน Callback ที่จะทำงานเมื่อมีข้อความเข้ามา
def callback(ch, method, properties, body):
    print(f" [x] Received Data...")
    
    # แปลง JSON กลับเป็น Python Dict
    order = json.loads(body)
    
    # จำลองการทำงาน (Processing)
    print(f"     Processing Order ID: {order['order_id']}")
    print(f"     Item: {order['product']} (Qty: {order['quantity']})")
    time.sleep(1) # จำลองว่าใช้เวลาทำงาน 1 วินาที
    
    print(" [v] Order Processed Done!")

    # สำคัญ! ส่ง Acknowledge บอก RabbitMQ ว่าทำงานเสร็จแล้ว (ลบออกจากคิวได้)
    ch.basic_ack(delivery_tag=method.delivery_tag)

# 2. ตั้งค่าการรับข้อมูล
# prefetch_count=1 คือให้ส่งงานมาทีละ 1 งาน ถ้ายังทำไม่เสร็จไม่ต้องส่งมาเพิ่ม (Fair dispatch)
channel.basic_qos(prefetch_count=1) 

channel.basic_consume(queue='order_queue', on_message_callback=callback)

# เริ่มวนลูปรอรับข้อมูล
channel.start_consuming()
```

### วิธีทดสอบ

1.  รัน Docker command
2.  เปิด Terminal อันที่ 1 รัน `python consumer.py` (มันจะรอรับข้อมูล)
3.  เปิด Terminal อันที่ 2 รัน `python producer.py` (มันจะยิง order เข้าไป)
4.  คุณจะเห็นที่หน้าจอ Consumer ว่ามันได้รับ Order และประมวลผลทีละรายการครับ

ต้องการให้เพิ่มส่วนไหนไหมครับ เช่น การจัดการ Error หรือการทำ Retry?
