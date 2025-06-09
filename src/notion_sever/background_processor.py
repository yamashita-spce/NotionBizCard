import threading
import main as process_cards_module

class BackgroundProcessor:
    def __init__(self):
        pass
    
    def start_background_process(self, business_card_path: str, hearing_seed_paths: list, lead_date: str, context: dict):
        """
        バックグラウンドで処理を開始（ジョブIDなどは不要）
        """
        # バックグラウンドで処理を開始
        thread = threading.Thread(
            target=self._process_in_background,
            args=(business_card_path, hearing_seed_paths, lead_date, context)
        )
        thread.daemon = True
        thread.start()
    
    
    def _process_in_background(self, business_card_path: str, hearing_seed_paths: list, lead_date: str, context: dict):
        """
        バックグラウンドで実際の処理を実行
        """
        try:
            print("[バックグラウンド] 処理を開始しています...")
            
            # 実際の処理を実行
            result_code = process_cards_module.main(
                business_card_path, hearing_seed_paths, lead_date, context
            )
            
            # 結果をログ出力
            if result_code == 0:
                print("[バックグラウンド] 処理が正常に完了しました")
            else:
                print(f"[バックグラウンド] 処理でエラーが発生しました (code: {result_code})")
                
        except Exception as e:
            print(f"[バックグラウンド] 処理中にエラーが発生しました: {e}")
    

# グローバルインスタンス
background_processor = BackgroundProcessor()