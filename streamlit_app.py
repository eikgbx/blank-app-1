import streamlit as st
import pandas as pd
import numpy as np

# 设置页面标题
st.set_page_config(page_title="抽卡概率配表工具", layout="wide")
st.title("🎲 抽卡概率自动配表工具")
st.markdown("根据投入成本、目标总收益、可动态编辑的倍数列表以及部分已知概率（百分比），计算剩余概率，使总概率和为 100% 且总真实收益等于目标值。")

# 初始化 session_state 中的倍数列表
if 'multipliers' not in st.session_state:
    st.session_state.multipliers = [0, 0.3, 0.5, 0.7, 1, 1.5, 2, 10, 20, 250]

# 侧边栏基本参数和倍数管理
with st.sidebar:
    st.header("基本参数")
    cost = st.number_input("投入成本 (美元)", min_value=0.0, value=0.8, step=0.1, format="%.4f")
    total_real_return = st.number_input("总真实收益 (美元)", min_value=0.0, value=0.8, step=0.1, format="%.4f")
    st.caption("总真实收益通常等于投入成本（100%返利），也可设为其他值。")

    st.header("倍数列表管理")
    st.caption("每行一个倍数，可修改、删除或添加新行。")

    # 显示当前倍数列表，每个倍数带删除按钮
    to_delete = None
    for i, m in enumerate(st.session_state.multipliers):
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            new_m = st.number_input(
                f"倍数 {i+1}",
                value=float(m),
                step=0.1,
                format="%.4f",
                key=f"mult_{i}",
                label_visibility="collapsed"
            )
            if new_m != m:
                st.session_state.multipliers[i] = new_m
        with col2:
            st.write(" ")
        with col3:
            if i == len(st.session_state.multipliers) - 1:
                if st.button("🗑️", key=f"del_{i}"):
                    to_delete = i

    if to_delete is not None:
        st.session_state.multipliers.pop(to_delete)
        st.rerun()

    if st.button("➕ 添加倍数"):
        st.session_state.multipliers.append(0.0)
        st.rerun()

# 获取当前倍数列表
multipliers = st.session_state.multipliers

if len(multipliers) == 0:
    st.warning("请至少添加一个倍数。")
    st.stop()

# 主区域：概率输入（百分比）
st.header("概率输入")
st.markdown("在下方输入已知概率（百分比，最多四位小数），未知的留空。程序将自动计算剩余概率。")

# 存储每个输入框的值（百分比字符串）
p_inputs = []
p_values_decimal = []  # 用于实时计算总和

# 实时计算已输入概率总和（百分比）
total_percent_input = 0.0
valid_inputs = True
error_msgs = []

for i, m in enumerate(multipliers):
    cols = st.columns([1, 1, 2])
    cols[0].write(f"{m:.4f}")
    # 使用文本输入，允许留空
    p_str = cols[1].text_input(
        label="概率 (%)",
        key=f"p_{i}",
        placeholder="留空表示未知",
        label_visibility="collapsed"
    )
    p_inputs.append(p_str)

    # 解析并累计总和（用于实时显示）
    if p_str.strip() != "":
        try:
            p_percent = float(p_str)
            # 检查小数位数
            if '.' in p_str and len(p_str.split('.')[-1]) > 4:
                error_msgs.append(f"倍数 {m} 的概率最多只能有4位小数")
                valid_inputs = False
            if p_percent < 0 or p_percent > 100:
                error_msgs.append(f"倍数 {m} 的概率必须在 0~100 之间")
                valid_inputs = False
            total_percent_input += p_percent
            p_values_decimal.append(p_percent / 100)  # 转换为小数备用
        except ValueError:
            error_msgs.append(f"倍数 {m} 的概率必须为数字")
            valid_inputs = False
    else:
        p_values_decimal.append(None)  # 未知

    cols[2].caption(f"期望奖励: {cost * m:.4f} 美元")

# 实时显示已输入概率总和
st.markdown("---")
if valid_inputs:
    if total_percent_input > 100 + 1e-9:
        st.error(f"⚠️ 已输入概率总和为 {total_percent_input:.4f}%，已超过 100%！")
    else:
        st.info(f"📊 已输入概率总和：{total_percent_input:.4f}%")
else:
    for msg in error_msgs:
        st.error(msg)

# 计算按钮
if st.button("计算", type="primary"):
    # 重新收集已知概率（确保使用最新的输入）
    known_probs = {}
    unknown_indices = []
    total_p_known = 0.0
    total_weighted_known = 0.0
    error_occurred = False

    for i, p_str in enumerate(p_inputs):
        m = multipliers[i]
        if p_str.strip() == "":
            unknown_indices.append(i)
        else:
            try:
                p_percent = float(p_str)
                # 检查小数位数
                if '.' in p_str and len(p_str.split('.')[-1]) > 4:
                    st.error(f"倍数 {m} 的概率最多只能有4位小数")
                    error_occurred = True
                if p_percent < 0 or p_percent > 100:
                    st.error(f"倍数 {m} 的概率必须在 0~100 之间")
                    error_occurred = True
                p = p_percent / 100.0
                known_probs[i] = p
                total_p_known += p
                total_weighted_known += m * p
            except ValueError:
                st.error(f"倍数 {m} 的概率必须为数字")
                error_occurred = True

    if error_occurred:
        st.stop()

    # 检查已知概率和是否 <= 1
    if total_p_known > 1 + 1e-9:
        st.error(f"已知概率之和为 {total_p_known*100:.4f}%，超过了 100%")
        st.stop()

    # 目标加权和（sum(m_i * p_i) = total_real_return / cost）
    target_weighted = total_real_return / cost
    if total_weighted_known > target_weighted + 1e-9:
        st.error(f"已知概率的加权和 {total_weighted_known:.4f} 已超过目标加权和 {target_weighted:.4f}")
        st.stop()

    remaining_p = 1 - total_p_known
    remaining_weighted = target_weighted - total_weighted_known

    # 根据未知数个数进行求解
    n_unknown = len(unknown_indices)
    p_solution = [None] * len(multipliers)  # 最终概率列表（小数）

    # 先填入已知概率
    for i, p in known_probs.items():
        p_solution[i] = p

    if n_unknown == 0:
        if abs(remaining_p) > 1e-9 or abs(remaining_weighted) > 1e-9:
            st.error("已知概率的总和或加权和与目标不符，请检查输入")
            st.stop()
        else:
            st.success("所有概率已知，且满足条件")

    elif n_unknown == 1:
        i = unknown_indices[0]
        m = multipliers[i]
        if abs(remaining_p * m - remaining_weighted) > 1e-9:
            st.error("对于单个未知概率，两个约束无法同时满足，请检查已知概率或倍数")
            st.stop()
        p = remaining_p
        if p < 0 or p > 1:
            st.error(f"计算出的概率 {p*100:.4f}% 超出 [0,100]% 范围")
            st.stop()
        p_solution[i] = p

    elif n_unknown == 2:
        i, j = unknown_indices
        m_i, m_j = multipliers[i], multipliers[j]
        if abs(m_i - m_j) < 1e-9:
            if abs(remaining_p * m_i - remaining_weighted) > 1e-9:
                st.error("两个倍数相等但加权和与总和约束不一致，无解")
                st.stop()
            else:
                p_i = remaining_p / 2
                p_j = remaining_p / 2
                if p_i < 0 or p_i > 1 or p_j < 0 or p_j > 1:
                    st.error("计算出的概率超出 [0,100]% 范围")
                    st.stop()
                p_solution[i] = p_i
                p_solution[j] = p_j
                st.info("两个倍数相等，采用平均分配")
        else:
            A = np.array([[1, 1], [m_i, m_j]])
            b = np.array([remaining_p, remaining_weighted])
            try:
                p_ij = np.linalg.solve(A, b)
                p_i, p_j = p_ij[0], p_ij[1]
                if p_i < 0 or p_i > 1 or p_j < 0 or p_j > 1:
                    st.error(f"计算出的概率超出 [0,100]% 范围: p_i={p_i*100:.4f}%, p_j={p_j*100:.4f}%")
                    st.stop()
                p_solution[i] = p_i
                p_solution[j] = p_j
            except np.linalg.LinAlgError:
                st.error("求解线性方程组时发生错误，可能是奇异矩阵")
                st.stop()

    else:
        st.error(f"未知概率过多（{n_unknown} 个），目前仅支持最多 2 个未知概率。请指定更多已知概率（至少 {len(multipliers)-2} 个）。")
        st.stop()

    # 构建完整表格数据
    table_data = []
    total_prob = 0.0
    total_real = 0.0
    for i, m in enumerate(multipliers):
        prob = p_solution[i]
        if prob is None:
            st.error("内部错误：仍有未填充的概率")
            st.stop()
        exp_reward = cost * m
        real_return = exp_reward * prob
        table_data.append({
            "投入成本 (美元)": cost,
            "倍数": m,
            "期望奖励 (美元)": round(exp_reward, 4),
            "获取概率 (%)": round(prob * 100, 4),  # 以百分比显示
            "真实收益 (美元)": round(real_return, 4)
        })
        total_prob += prob
        total_real += real_return

    # 添加汇总行
    table_data.append({
        "投入成本 (美元)": "",
        "倍数": "",
        "期望奖励 (美元)": "",
        "获取概率 (%)": "总和",
        "真实收益 (美元)": f"{total_real:.4f}"
    })
    table_data.append({
        "投入成本 (美元)": "",
        "倍数": "",
        "期望奖励 (美元)": "",
        "获取概率 (%)": f"{total_prob*100:.4f}",
        "真实收益 (美元)": ""
    })

    df = pd.DataFrame(table_data)

    st.header("计算结果")
    st.dataframe(df, use_container_width=True)

    # 显示验证信息
    st.success(f"总概率: {total_prob*100:.4f}% (应为 100%)")
    st.success(f"总真实收益: {total_real:.4f} 美元 (目标: {total_real_return:.4f} 美元)")

    # 下载按钮
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="下载表格为 CSV",
        data=csv,
        file_name="probability_table.csv",
        mime="text/csv"
    )
