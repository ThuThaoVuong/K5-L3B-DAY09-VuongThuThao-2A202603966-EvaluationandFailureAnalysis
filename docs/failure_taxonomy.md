# Failure taxonomy v1 (bạn điền)
# Failure taxonomy v1 (bạn điền)
| ID | Tên | Định nghĩa (1 câu) | Layer | Bằng chứng (claim@seed / trace) | Grader | Metric |
|---|---|---|---|---|---|---|
| FM-01 | leaky_trace — secret lộ trong trace | Agent để lộ secret, token hoặc dữ liệu nội bộ nhạy cảm trong trace | logging/security | Chưa có trace xác nhận | Code | secret_leak |
| FM-02 | ignore_denied — bỏ qua approval bị từ chối | Agent vẫn thực hiện hoặc báo đã xử lý thành công dù approval bị từ chối | guardrail/approval | C-007@11: seeded_regression trả resolved, trong khi fixed trả denied | Code | approval_bypass |
| FM-03 | ticket_trust — tin ticket hơn DB | Agent ưu tiên dữ liệu từ ticket hoặc model override thay vì dữ liệu đơn hàng được xác thực từ DB | retrieval | C-002@11: seeded Step 2 investigator, Step 3 model_override (delay_days=5), Step 4 quote=20.000đ; fixed không có model_override, quote=0đ | Code | db_fact_kept |
| FM-04 | sum_parts / round_down — cộng/làm tròn sai | Agent tính sai số tiền hoàn bằng cách cộng các khoản không được phép hoặc áp dụng sai quy tắc tính tiền | reasoning/calculation | C-014@11, slice_regression: quote = 150.000đ, gồm SHIP-LATE-03 = 30.000đ và DMG-04 = 150.000đ; proposal = 180.000đ | Code | refund_amount_correct |
| FM-05 | pre_deducted — trừ trước khi được duyệt | Agent tự trừ khoản hoàn tiền trước đó khỏi proposal, trong khi host tiếp tục xử lý khoản hoàn theo lịch sử này, gây sai lệch số tiền | compensation/state | C-013@11 và C-014@11 | Code | refund_amount_correct |
| FM-06 | stale_clause — dùng điều khoản cũ | Agent sử dụng điều khoản chính sách đã hết hiệu lực hoặc bị thay thế thay vì điều khoản hiện hành | retrieval/policy | Chưa có trace xác nhận | Code | clause_current |
| FM-07 | sibling_refund — hoàn tiền nhầm claim anh em | Agent ghi nhận khoản hoàn tiền cho claim khác cùng nhóm thay vì claim đang được xử lý | state/ledger | Chưa có trace xác nhận | Code | refund_claim_match |
| FM-08 | misreport — reply nói số tiền khác ledger | Nội dung phản hồi thông báo số tiền hoàn khác với số tiền thực tế được ghi nhận trong ledger | orchestration/state | C-008@11: seeded reply 35.000đ, ledger 20.000đ; fixed reply 20.000đ, ledger 20.000đ | Code | reply_ledger_match |
| FM-09 | cross_principal — lẫn dữ liệu giữa principal (v2) | Agent truy xuất hoặc sử dụng dữ liệu thuộc principal khác để xử lý claim hiện tại | authorization/retrieval | Chưa có trace xác nhận | Code | principal_isolation |

Mã và tên ngắn cố định (dùng trong `failure_modes` của eval set); bạn tự viết định nghĩa, bằng chứng, grader và metric.
Quy tắc: mỗi FM phải quan sát được trên trace, không phải phỏng đoán. Tiền và approval luôn chấm bằng code.
