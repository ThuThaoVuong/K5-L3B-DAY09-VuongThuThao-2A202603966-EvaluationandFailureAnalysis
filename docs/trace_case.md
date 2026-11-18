# Trace case: từ trace tới quyết định sai đầu tiên

Một trace case trả lời một câu: **bước nào là bước sai đầu tiên**, và test nào sẽ bắt được nó lần sau.

```bash
cd src
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11   # đối chứng
```

Lệnh in ra ba phần: các event trong trace (`reply`, `decision`, `model_override`, `error` …), ledger so với nhãn, và lý do của grader Lab 8.

## Mẫu điền (mỗi bạn 1 case, lấy từ trial đang fail trong report)

| Trường | Nội dung |
|---|---|
| Trial | `seeded_regression C-002@11`, run ID trong report |
| Triệu chứng | Lab 8 grader FAIL (status resolved != denied). Ledger ghi hoàn 20.000đ, hoàn 1 lần, trạng thái resolved, trong khi nhãn chuẩn yêu cầu hoàn 0đ, 0 lần và denied. Reply thông báo đã hoàn 20.000đ cho đơn O-202. |
| Bước sai đầu tiên | Event 3 – model_override: {"delay_days": 5} |
| Vì sao là bước *đầu tiên* |Event 1 (handoff) thiết lập phạm vi xử lý và các công cụ được phép sử dụng. Event 2 (investigator) tra cứu đơn hàng thành công. Event 3 xuất hiện dữ liệu override delay_days=5, làm thay đổi dữ kiện dùng để xét điều kiện chính sách. Event 4 mới tính khoản hoàn 20.000đ dựa trên dữ kiện sai này.|
| Failure mode | Mã FM-03 – ticket_trust trong `docs/failure_taxonomy.md` |
| Đối chứng | Với `fixed C-002@11`, event 3 model_override không còn xuất hiện. Event 3 lúc này là quote, kết quả amount_vnd=0, reason=no_entitlement. Ledger ghi hoàn 0đ, 0 lần, trạng thái denied; grader PASS. |
| Regression test |Có tests/test_swarm_reference.py, kiểm tra C-002 với seed 11 và 55. Tuy nhiên, test này kiểm tra reference swarm, không thể khẳng định nó trực tiếp tái hiện lỗi seeded_regression  |
| Chưa chắc chắn | Trace chứng minh override xuất hiện trước khi tính khoản hoàn tiền và kết quả ledger sai so với nhãn. Tuy nhiên, trace chưa chứng minh nguyên nhân nội bộ khiến model tạo ra override này. |

## Quy tắc

- Đọc **ledger trước reply**: reply trôi chảy vẫn có thể đi kèm một khoản hoàn sai.
- "Bước sai đầu tiên" phải dẫn số event cụ thể, không phải "agent bị nhầm".
- Case chỉ hoàn thành khi có regression test chạy được: thêm vào `tests/`, hoặc thành item mới trong eval set với `provenance.from_trace`.
