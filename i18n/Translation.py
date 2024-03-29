# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

import bpy

ctxt = "Pencil4"

translation_dict = {
    "ja_JP": {
        ("*", "Pencil+ 4 Line"):
            "Pencil+ 4 ライン",

        #
        (ctxt, "Color"):
            "色",
        (ctxt, "Background Color"):
            "背景色",
        (ctxt, "Size"):
            "サイズ",
        (ctxt, "Length"):
            "長さ",
        (ctxt, "Angle"):
            "角度",
        (ctxt, "Stretch"):
            "ストレッチ",
        (ctxt, "Antialiasing"):
            "アンチエイリアス",
        (ctxt, "Random"):
            "ランダム",
        (ctxt, "Random Seed"):
            "ランダムシード",
        (ctxt, "Amount"):
            "量",
        (ctxt, "Opacity"):
            "不透明度",
        (ctxt, "Number"):
            "数",
        (ctxt, "Min"):
            "最小",
        (ctxt, "Max"):
            "最大",
        (ctxt, "Start"):
            "開始",
        (ctxt, "End"):
            "終了",
        (ctxt, "Output"):
            "出力",
        (ctxt, "Brush"):
            "ブラシ",
        (ctxt, "Edge"):
            "エッジ",
        (ctxt, "Stroke"):
            "ストローク",
        (ctxt, "Objects"):
            "オブジェクト",
        (ctxt, "Materials"):
            "マテリアル",
        (ctxt, "Line Sets"):
            "ラインセット",
        (ctxt, "Line List"):
            "ラインリスト",
        (ctxt, "Add Objects"):
            "オブジェクトを追加",
        (ctxt, "Remove Objects"):
            "オブジェクトを削除",
        (ctxt, "Add Materials"):
            "マテリアルを追加",
        (ctxt, "Remove Materials"):
            "マテリアルを削除",
        (ctxt, "On"):
            "オン",
        (ctxt, "Off"):
            "オフ",
        (ctxt, "Retry"):
            "リトライ",
        (ctxt, "New"):
            "新規",
        (ctxt, "Source"):
            "ソース",
        (ctxt, "Index"):
            "インデックス",
        (ctxt, "Name"):
            "名前",

        # Line Node
        (ctxt, "Line"):
            "ライン",
        (ctxt, "Pencil+ 4 Line Parameters"):
            "Pencil+ 4 ラインのパラメータ",
        (ctxt, "Render Priority"):
            "描画の優先度",
        (ctxt, "Line Size"):
            "ラインサイズ",
        ("*", "Relative (640*480)"):
            "相対 (640*480 基準)",
        (ctxt, "Output to Render Elements Only"):
            "レンダーエレメントにのみ出力",
        (ctxt, "Over Sampling"):
            "オーバーサンプリング",
        (ctxt, "Offscreen Distance"):
            "画面外距離",

        # Line Set
        (ctxt, "Line Set"):
            "ラインセット",
        (ctxt, "Line Set ID"):
            "ラインセットID",
        (ctxt, "Visible Lines"):
            "可視線",
        (ctxt, "Hidden Lines"):
            "隠線",
        (ctxt, "Outline"):
            "アウトライン",
        (ctxt, "Object"):
            "オブジェクト",
        (ctxt, "Intersection"):
            "交差",
        (ctxt, "Smoothing Boundary"):
            "スムージング境界",
        (ctxt, "Material ID Boundary"):
            "マテリアルID境界",
        (ctxt, "Selected Edges"):
            "選択エッジ",
        (ctxt, "Normal Angle"):
            "法線角度",
        (ctxt, "Wireframe"):
            "ワイヤ",
        (ctxt, "Open Edge"):
            "オープンエッジ",
        (ctxt, "Merge Groups"):
            "グループを結合",
        (ctxt, "Self-Intersection"):
            "自己交差",
        (ctxt, "Specific Brush Settings"):
            "個別のブラシ設定",
        (ctxt, "Reduction"):
            "減衰",
        (ctxt, "Size Reduction"):
            "サイズの縮小",
        (ctxt, "Alpha Reduction"):
            "アルファの減衰",

        (ctxt, "V Brush Settings"):
            "可視線 ブラシ設定",
        (ctxt, "H Brush Settings"):
            "隠線 ブラシ設定",

        (ctxt, "V Outline"):
            "可視線 アウトライン",
        (ctxt, "H Outline"):
            "隠線 アウトライン",
        (ctxt, "V Object"):
            "可視線 オブジェクト",
        (ctxt, "H Object"):
            "隠線 オブジェクト",
        (ctxt, "V Intersection"):
            "可視線 交差",
        (ctxt, "H Intersection"):
            "隠線 交差",
        (ctxt, "V Smoothing"):
            "可視線 スムージング",
        (ctxt, "H Smoothing"):
            "隠線 スムージング",
        (ctxt, "V Material ID"):
            "可視線 マテリアルID",
        (ctxt, "H Material ID"):
            "隠線 マテリアルID",
        (ctxt, "V Selected Edges"):
            "可視線 選択エッジ",
        (ctxt, "H Selected Edges"):
            "隠線 選択エッジ",
        (ctxt, "V Normal Angle"):
            "可視線 法線角度",
        (ctxt, "H Normal Angle"):
            "隠線 法線角度",
        (ctxt, "V Wireframe"):
            "可視線 ワイヤ",
        (ctxt, "H Wireframe"):
            "隠線 ワイヤ",
        (ctxt, "V Size Reduction"):
            "可視線 サイズ縮小",
        (ctxt, "H Size Reduction"):
            "隠線 サイズ縮小",
        (ctxt, "V Alpha Reduction"):
            "可視線 アルファ減衰",
        (ctxt, "H Alpha Reduction"):
            "隠線 アルファ減衰",

        (ctxt, "Weld Edges Between Objects"):
            "オブジェクト間でエッジを連結する",
        (ctxt, "Mask Hidden Lines of Other Line Sets"):
            "他のラインセットの隠線を遮へいする ",

        # Brush Settings
        (ctxt, "Brush Settings"):
            "ブラシ設定",
        (ctxt, "Blend Amount"):
            "ブレンド量",
        (ctxt, "Color Map"):
            "カラーマップ",
        (ctxt, "Size Map"):
            "サイズマップ",

        # Brush Detail
        (ctxt, "Brush Detail"):
            "ブラシ詳細設定",
        (ctxt, "Brush Editor"):
            "ブラシエディター",
        (ctxt, "Brush Type"):
            "ブラシの種類",
        (ctxt, "Normal"):
            "通常",
        (ctxt, "Multiple"):
            "複数",
        (ctxt, "Simple"):
            "単純",
        (ctxt, "Brush Map"):
            "ブラシマップ",
        (ctxt, "Groove"):
            "溝",
        (ctxt, "Groove Number"):
            "溝の数",
        (ctxt, "Horizontal Space"):
            "水平間隔",
        (ctxt, "Vertical Space"):
            "垂直間隔",

        (ctxt, "Stroke Type"):
            "ストロークの種類",
        (ctxt, "Rake"):
            "レーキ",
        (ctxt, "Line Type"):
            "線の種類",
        (ctxt, "Full"):
            "実線",
        (ctxt, "Dashed"):
            "破線",
        (ctxt, "Space"):
            "間隔",
        (ctxt, "Extend"):
            "はみ出し",
        (ctxt, "Line Copy"):
            "ラインの複製",
        (ctxt, "Normal Offset"):
            "法線オフセット",
        (ctxt, "X Offset"):
            "Xオフセット",
        (ctxt, "Y Offset"):
            "Yオフセット",
        (ctxt, "Line Split Angle"):
            "ライン分断角度",
        (ctxt, "Min Line Length"):
            "最小ライン長",
        (ctxt, "Line Link Length"):
            "ライン結合長",
        (ctxt, "Line Direction (Angle)"):
            "線の方向 (角度)",
        (ctxt, "Loop Direction"):
            "ループ時の方向",
        (ctxt, "Anticlockwise"):
            "反時計回り",
        (ctxt, "Clockwise"):
            "時計回り",

        (ctxt, "Distortion"):
            "ゆがみ",
        (ctxt, "Distortion Map"):
            "ゆがみマップ",
        (ctxt, "Cycles"):
            "周期",
        (ctxt, "Phase"):
            "位相",

        (ctxt, "Stroke Size Reduction Settings"):
            "ストローク サイズ減衰",
        (ctxt, "Stroke Alpha Reduction Settings"):
            "ストローク アルファ減衰",

        (ctxt, "Color Range"):
            "カラー範囲",

        # Reduction Settings
        (ctxt, "Reduction Settings"):
            "減衰設定",
        (ctxt, "Start and End"):
            "開始と終了",
        (ctxt, "Refer Object"):
            "オブジェクトの参照",

        # Texture Map
        (ctxt, "Texture Map"):
            "テクスチャマップ",
        (ctxt, "Source Type"):
            "ソース種別",
        (ctxt, "Selection Mode"):
            "選択モード",
        ("*", "Object Color"):
            "オブジェクト カラー",
        (ctxt, "Image and UV"):
            "画像とUV",
        (ctxt, "Wrap Mode U"):
            "ラップモード U",
        ("*", "Mirror Once"):
            "ミラー (一度だけ)",
        (ctxt, "Filter Mode"):
            "フィルターモード",
        (ctxt, "UV Source"):
            "UVソース",
        (ctxt, "Tiling U"):
            "タイリング U",
        (ctxt, "Offset U"):
            "オフセット U",
        ("*", "Object UV"):
            "オブジェクト UV",
        (ctxt, "Color Attribute"):
            "カラー属性",

        # Line Functions
        (ctxt, "Pencil+ 4 Line Functions"):
            "Pencil+ 4 ライン関連機能",
        (ctxt, "Replace Line Color"):
            "ラインカラーの置き換え",
        (ctxt, "Edge Detection"):
            "エッジ検出設定",
        (ctxt, "Disable Intersection"):
            "交差判定を無効にする",
        (ctxt, "Draw Hidden Lines as Visible Lines"):
            "すべての隠線を可視線として描画",
        (ctxt, "Draw Hidden Lines of Targets as Visible Lines"):
            "対象の隠線を可視線として描画",
        (ctxt, "Mask Hidden Lines of Targets"):
            "対象の隠線を遮へいする",

        # Node Tree Menu
        (ctxt, "Cleanup Lists in Line Set Nodes"):
            "ラインセットノード中のリストをクリーンアップする",
        (ctxt, "Merge into Another Line Node Tree"):
            "他のラインノードツリーへ合成する",
        (ctxt, "Merge Options"):
            "合成オプション",
        (ctxt, "Replace Same Name Lines"):
            "同名のラインを置換する",
        (ctxt, "Fix Unused Library Objects by Name Matching"):
            "名前の合致で未使用のライブラリオブジェクトを修正",
        (ctxt, "Fix Unused Library Materials by Name Matching"):
            "名前の合致で未使用のライブラリマテリアルを修正",
        (ctxt, "Delete Unused Materials"):
            "未使用のマテリアルを削除",
        (ctxt, "Delete Unused Objects"):
            "未使用のオブジェクトを削除",

        # Render Element
        (ctxt, "Render Element"):
            "レンダーエレメント",
        (ctxt, "Pencil+ 4 Line Render Element"):
            "Pencil+ 4 ライン レンダーエレメント",
        (ctxt, "Z Depth"):
            "Z深度",
        (ctxt, "Z Min"):
            "Z最小値",
        (ctxt, "Z Max"):
            "Z最大値",
        (ctxt, "Output Element"):
            "出力する要素",
        (ctxt, "Output Categories"):
            "出力するカテゴリ",
        (ctxt, "Output Edges"):
            "出力するエッジ",
        (ctxt, "Output Line Set IDs"):
            "出力するラインセットID",

        # Vector File Output
        (ctxt, "Vector File Output"):
            "ベクトルファイル出力",
        (ctxt, "Base Path"):
            "基本パス",
        (ctxt, "Outputs"):
            "出力",
        (ctxt, "File Subpath"):
            "ファイルサブパス",
        (ctxt, "File Type"):
            "ファイルタイプ",

        # Line Group
        (ctxt, "Pencil+ 4 Line Group"):
            "Pencil+ 4 ライン グループ",

        # Line Merge Helper
        (ctxt, "Line Merge Helper"):
            "ライン合成ヘルパー",

        # Viewport Rendering
        (ctxt, "Viewport Display"):
            "ビューポート表示",
        (ctxt, "Line Preview"):
            "ライン プレビュー",
        (ctxt, "Adjust Timeout Period"):
            "タイムアウト時間の調整",
        (ctxt, "Camera View Option"):
            "カメラビュー オプション",
        (ctxt, "Line Size Adjustment"):
            "ラインサイズ調整",
        (ctxt, "Viewport Render"):
            "ビューポートレンダー",
        (ctxt, "Render Image"):
            "画像をレンダリング",
        (ctxt, "Render Animation"):
            "アニメーションをレンダリング",
        (ctxt, "Render Keyframes"):
            "キーフレームをレンダリング",

        # Attribute Override
        (ctxt, "Attribute Override"):
            "属性オーバーライド",
        (ctxt, "Attribute Override (Scene)"):
            "属性オーバーライド (シーン)",
        (ctxt, "Attribute Override (ViewLayer)"):
            "属性オーバーライド (ビューレイヤー)",

        # Preferences
        (ctxt, "Show Preferences"):
            "プリファレンスを表示",
        (ctxt, "PSOFT Pencil+ 4 Render App Path"):
            "PSOFT Pencil+ 4 Render App パス",
        (ctxt, "Viewport Preview Timeout Period"):
            "ビューポートプレビューのタイムアウト時間",
        (ctxt, "Abort Rendering when Errors Occur"):
            "エラー発生時にレンダリングを中断する",

        (ctxt, "If deleting or uninstalling the add-on fails,"):
            "アドオンの削除や再インストールに失敗する場合、",
        (ctxt, "please try the following."):
            "以下の手順を試してください。",
        (ctxt, "1. Open the Pencil+ 4 Line add-on folder."):
            "1. Pencil+ 4 Line アドオン フォルダーを開く。",
        (ctxt, "2. Terminate all Blender processes."):
            "2. 全てのBlenderプロセスを終了する。",
        (ctxt, "3. Delete all the items in the Pencil+ 4 Line add-on folder."):
            "3. Pencil+ 4 Line アドオン フォルダー内の全ての項目を削除する。",

        (ctxt, "Show Details"):
            "詳細を表示",
        (ctxt, "The add-on is not properly installed."):
            "アドオンが正しくインストールされていません。",
        (ctxt, "Please reinstall the add-on."):
            "アドオンを再インストールしてください。",
        (ctxt, "If the installation fails, try removing the add-on following the steps below."):
            "インストールに失敗する場合は、以下の手順に従ってアドオンを削除してください。",
    }
}
