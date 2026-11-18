# Judge audit

Chạy: `python -m lab9.judge --csv <file> --audit 5`

| Tiêu chí | n | κ | Precision | Recall | Đạt FLOORS (κ≥0.6, P≥0.8, R≥0.7)? | Quyết định |
|---|---|---|---|---|---|---|
| tone_ok | 100 | 0.757 | 0.857 | 0.800 | PASS | dùng |
| helpful | 100 | 0.375 | 1.000 | 0.300 | FAIL | loại |

## ≥5 case audit thủ công

| # | Case | Judge nói | Người nói | Ai đúng? | Ghi chú |
|---|---|---|---|---|---|
| 1 | HL-015 | PASS | FAIL | Người | Câu trả lời chỉ thông báo hoàn tiền, chưa thể hiện đầy đủ tính hữu ích theo tiêu chí đánh giá. |
| 2 | HL-016 | PASS | FAIL | Người | Lời xin lỗi mang tính xã giao, chưa cung cấp thông tin hỗ trợ cụ thể. |
| 3 | HL-020 | PASS | FAIL | Người | Chỉ thông báo số tiền hoàn, chưa giải quyết đầy đủ nhu cầu của khách hàng. |
| 4 | HL-028 | PASS | FAIL | Người | Nội dung xin lỗi chung chung, thiếu thông tin xử lý vấn đề. |
| 5 | HL-035 | PASS | FAIL | Người | Lời xin lỗi chưa đi kèm hướng giải quyết cụ thể. |
| 6 | H-008 | PASS | FAIL | Người | Cách diễn đạt quá thân mật ("nha"), chưa phù hợp với giọng điệu chuyên nghiệp. |
| 7 | H-017 | PASS | FAIL | Người | Sử dụng cách xưng hô và diễn đạt thân mật, chưa đảm bảo tính chuyên nghiệp. |
| 8 | H-029 | PASS | FAIL | Người | Câu trả lời mang tính ra lệnh, thiếu sự lịch sự và thân thiện. |
| 9 | H-042 | FAIL | PASS | Người | Câu trả lời lịch sự, rõ ràng và có thông tin thời gian hoàn tiền cụ thể. |
| 10 | H-051 | FAIL | PASS | Người | Câu trả lời ngắn gọn, lịch sự và cung cấp thông tin hoàn tiền phù hợp. |

## Kết luận

**1. Quyết định sử dụng Judge**

- **tone_ok – Được sử dụng:** Đạt cả ba ngưỡng FLOORS với κ = 0.757, Precision = 0.857 và Recall = 0.800. Judge có mức độ đồng thuận tương đối tốt với nhãn của con người, có thể sử dụng để đánh giá tiêu chí tone_ok.

- **helpful – Bị loại:** Không đạt FLOORS với κ = 0.375 và Recall = 0.300, mặc dù Precision = 1.000. Judge bỏ sót nhiều trường hợp không hữu ích, khiến kết quả đánh giá chưa đáng tin cậy.

**2. Phân tích ma trận nhầm lẫn**

- **tone_ok:** TP = 24, FP = 4, FN = 6, TN = 66. Judge có 10 trường hợp dự đoán sai, trong đó có 6 trường hợp bỏ sót và 4 trường hợp đánh giá nhầm.
- **helpful:** TP = 9, FP = 0, FN = 21, TN = 70. Judge bỏ sót 21 trường hợp thuộc nhãn FAIL, cho thấy khả năng nhận diện câu trả lời không hữu ích còn yếu.

**3. Rủi ro còn lại**

Judge hiện chỉ được kiểm thử trên dữ liệu replay đã công khai. Vì vậy, kết quả chưa đảm bảo khả năng tổng quát hóa trên dữ liệu thực tế hoặc dữ liệu mới. Cần thu thập thêm nhãn do con người đánh giá trên một tập dữ liệu held-out độc lập để kiểm chứng độ tin cậy của Judge.