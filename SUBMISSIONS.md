# Submit predictions through Hugging Face

Open the [competition Space](https://huggingface.co/spaces/HulaEarth/ai-for-nature-hula-earth) and choose **Submit**, or [open the Submit tab directly](https://hulaearth-ai-for-nature-hula-earth.static.hf.space/index.html#submit).

1. Open **Register** on the Space, sign in with Hugging Face and create your team once. Wait for confirmation. The captain can invite teammates by their Hugging Face usernames. Invitations appear in Register; no email is sent.
2. Teammates sign in and accept an invitation to join. Any confirmed team member can upload. Use **Practice** and the supplied 120-row CSV to check delivery early. Practice produces no model score or final scoring attempt.
3. After test unlock, choose **Final test**, your prediction CSV and the supplied final sample for the local row-ID check. Submit directly. The browser handles encryption and delivery.
4. Keep the receipt and check **Accepted**. Upload received is not yet acceptance.
5. Leave **Make this my final entry if accepted** checked, or use **Use for final** beside an accepted final entry. Check confirmation before **17:30 German time**.

Final CSVs contain exactly 159,150 rows with the header `row_id,score`, every supplied ID once and finite scores in [0,1]. Maximum size: 8 MB. Five accepted final predictions apply per team across the entire event and both delivery routes. Rejections use no accepted attempt and preserve the earlier final choice. **Only the captain can choose the final model.** Use **Use for final** beside any accepted team prediction, including a teammate’s upload, and verify the highlighted **Final choice** before 17:30. This uses no new prediction attempt. Without an explicit choice, the latest accepted captain upload is used. If only teammates uploaded, the captain must choose an entry.

The original unedited HF server comment binds SHA256 of the exact request manifest, which commits to the ciphertext fingerprint and final-choice instruction. That server timestamp controls eligibility; Git commit dates, browser clocks and later evaluation times do not. Complete the transfer before the deadline and leave time to check acceptance. Keep requests unchanged.

Sessions last one hour. Tokens remain in memory. Pending receipt metadata survives a reload and sign-in, without saving CSVs or tokens. Refresh checks existing results and never resubmits a file. If a transfer is stopped or interrupted, its status is unconfirmed because it may still have reached the provider; check before trying again.

Upload the presentation PDF through the separate Google Form linked below prediction submission. Enter your public method/report and code/checkpoint reference before submitting the final CSV, or when sending a later final choice with **Use for final**. Complete the reproducibility report. Do not publish passwords, keys, hidden labels or a raw final CSV.

If a conductor asks you to use backup delivery, open **legacy-submit.html#submit** on the same Space. Legacy GitHub teams retain their attachment and nomination forms with the same quota and final selection. Native Hugging Face teams should ask the conductor to recover the original receipt rather than create a second team or use an unbound GitHub account. Receipts are labelled `HF-N` and `GH-N` so numbers cannot collide.

Leaderboard ranking follows the captain’s **currently selected model**, using its public AP during the event and its private AP after final evaluation. Switching the choice updates the public score and rank. A member-only upload needs a captain choice; otherwise the latest captain upload is the fallback. Earlier accepted scores remain in the team entry history.
