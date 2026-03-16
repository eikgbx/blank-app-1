import streamlit as st
import pandas as pd
import numpy as np

# 页面配置
st.set_page_config(page_title="抽卡概率表配比工具（百分比输入）", layout="wide")
st.title("🎲 抽卡概率表自动配比工具（百分比输入）")

# 初始化 session_state 中的存储 DataFrame（概率为小数）
if "df_storage" not in st.session_state:
    # 默认示例数据（概率为小数）
    default_data = {
        "倍数": [0, 0.3, 0.5, 0.7, 1, 1.5, 2, 10, 20, 250],
        "概率": [0.15, 0.0915, 0.15, 0.20, 0.20, 0.1085, 0.0849, 0.01, 0.005, 0.0001]
    }
    st.session_state.df_storage = pd.DataFrame(default_data)

# 侧边栏输入参数
with st.sidebar:
    st.header("⚙️ 全局参数")
    cost = st.number_input("投入成本 (C)", min_value=0.01, value=0.8, step=0.01, format="%.2f")
    total_return = st.number_input("目标总真实收益", min_value=0.0, value=cost, step=0.01, format="%.2f",
                                   help="通常等于投入成本（100%返利）")
    st.caption("当前目标总真实收益 = {:.4f}".format(total_return))
    st.divider()
    st.subheader("📊 当前统计")

# 根据存储数据构造显示用 DataFrame（概率乘以100，变为百分比数值）
df_storage = st.session_state.df_storage.copy()
df_display = df_storage.copy()
df_display["概率"] = df_storage["概率"] * 100  # 转为百分比数值

# 显示可编辑表格（倍数和百分比概率可编辑，真实收益只读）
st.subheader("✏️ 编辑档位数据（概率请直接输入百分比数值，如15表示15%）")
edited_display_df = st.data_editor(
    df_display,
    column_config={
        "倍数": st.column_config.NumberColumn("倍数", min_value=0.0, step=0.1, format="%.2f"),
        "概率": st.column_config.NumberColumn("概率 (%)", min_value=0.0, step=0.01, format="%.4f",
                                               help="输入百分比数值，例如 15 表示 15%，0.01 表示 0.01%"),
        # 真实收益列暂不显示在编辑器中，避免混淆
    },
    num_rows="dynamic",
    use_container_width=True,
    key="data_editor",
    disabled=False,
    hide_index=True,
)

# 检测用户是否编辑了表格（通过比较编辑后的 DataFrame 与当前显示用的 df_display）
# 注意：由于浮点误差，使用近似比较
if not edited_display_df[["倍数", "概率"]].equals(df_display[["倍数", "概率"]]):
    # 用户编辑了，将编辑后的数据转换为小数概率存入 storage
    new_storage = edited_display_df.copy()
    new_storage["概率"] = new_storage["概率"] / 100.0  # 百分比转小数
    st.session_state.df_storage = new_storage
    st.rerun()  # 立即重新运行以更新显示

# 重新获取最新的存储 df（确保一致）
df_storage = st.session_state.df_storage.copy()

# 计算当前总概率（小数）和总真实收益
total_prob = df_storage["概率"].sum()
total_real = cost * (df_storage["倍数"] * df_storage["概率"]).sum()

# 计算剩余概率和剩余真实收益需求
prob_rem = 1.0 - total_prob
real_rem = total_return - total_real

# 在侧边栏更新统计信息
with st.sidebar:
    st.metric("当前总概率", f"{total_prob:.4f}", delta=f"{prob_rem:+.4f}" if abs(prob_rem) > 1e-6 else "正好1")
    st.metric("当前总真实收益", f"{total_real:.6f}", delta=f"{real_rem:+.6f}" if abs(real_rem) > 1e-6 else "正好目标")
    if prob_rem < -1e-6:
        st.error(f"❌ 总概率已超过1，超出 {abs(prob_rem):.4f}")
    elif prob_rem > 1e-6:
        st.info(f"剩余概率: {prob_rem:.4f}")
        if abs(real_rem) < 1e-9:
            st.success("剩余真实收益需求为 0，缺失档位倍率应为 0")
        elif cost > 0 and prob_rem > 0:
            m_rem = real_rem / (cost * prob_rem)
            st.info(f"缺失档位倍率需为: **{m_rem:.4f}**")
            if m_rem < 0:
                st.warning("⚠️ 倍率为负，请检查输入是否合理")
    elif abs(prob_rem) <= 1e-6:
        if abs(real_rem) > 1e-6:
            st.error(f"❌ 总概率为1但真实收益偏差 {real_rem:.6f}，无法满足目标")
        else:
            st.success("✅ 当前已完美满足条件")

# 添加缺失档位的按钮
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("➕ 添加缺失档位"):
        if prob_rem <= 1e-6:
            st.warning("没有剩余概率，无法添加缺失档位")
        elif cost <= 0:
            st.error("投入成本必须大于0")
        else:
            m_rem = real_rem / (cost * prob_rem)
            # 添加新行（倍率可能为负，但允许）
            new_row = pd.DataFrame({"倍数": [m_rem], "概率": [prob_rem]})
            st.session_state.df_storage = pd.concat([st.session_state.df_storage, new_row], ignore_index=True)
            st.rerun()

with col2:
    if st.button("🔄 重置为示例数据"):
        default_data = {
            "倍数": [0, 0.3, 0.5, 0.7, 1, 1.5, 2, 10, 20, 250],
            "概率": [0.15, 0.0915, 0.15, 0.20, 0.20, 0.1085, 0.0849, 0.01, 0.005, 0.0001]
        }
        st.session_state.df_storage = pd.DataFrame(default_data)
        st.rerun()

with col3:
    if st.button("🗑️ 清空所有行"):
        st.session_state.df_storage = pd.DataFrame({"倍数": [0.0], "概率": [0.0]})
        st.rerun()

# 显示完整的配比表格（包含期望奖励和真实收益）
st.subheader("📋 当前完整配比表")
result_df = df_storage.copy()
result_df["期望奖励"] = cost * result_df["倍数"]
result_df["真实收益"] = cost * result_df["倍数"] * result_df["概率"]
result_df["真实收益"] = result_df["真实收益"].round(6)
# 添加一列百分比概率方便查看
result_df["概率 (%)"] = result_df["概率"] * 100
st.dataframe(result_df[["倍数", "概率 (%)", "期望奖励", "真实收益"]], use_container_width=True)

# 底部汇总
st.divider()
st.write("💡 使用说明：")
st.markdown("""
- **投入成本** 和 **目标总真实收益** 在左侧边栏设置。
- 在表格中编辑各档位的 **倍数** 和 **概率**，概率请直接输入百分比数值（例如 15 表示 15%，0.01 表示 0.01%）。
- 右侧边栏实时显示当前总概率、总真实收益，并自动计算 **缺失档位** 所需的倍数。
- 点击 **添加缺失档位** 可将计算出的档位加入表格。
- 当总概率为1且总真实收益等于目标时，表格满足要求。
""")
