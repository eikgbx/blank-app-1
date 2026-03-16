import streamlit as st
import pandas as pd
import numpy as np

import hmac

# ---------- 密码验证函数 ----------
def check_password():
    """返回 `True` 如果用户输入了正确的密码"""

    def password_entered():
        """检查密码是否正确"""
        if hmac.compare_digest(st.session_state["password"], st.secrets["PASSWORD"]):
            st.session_state["password_correct"] = True
            # 删除已经输入的密码，避免它留在 session_state 中
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    # 如果已经认证通过，直接返回 True
    if st.session_state.get("password_correct", False):
        return True

    # 显示密码输入框
    st.text_input(
        "请输入访问密码",
        type="password",
        on_change=password_entered,
        key="password",
    )
    if "password_correct" in st.session_state:
        st.error("😕 密码错误，请重试")
    return False

# ---------- 应用入口 ----------
if not check_password():
    st.stop()  # 密码错误时停止执行后续代码

# ... 你的抽卡概率计算器代码从这里开始 ...

# 设置页面标题
st.set_page_config(page_title="抽卡概率配表工具", layout="wide")
st.title("🎲 抽卡概率自动配表工具")
st.markdown("根据投入成本、目标总收益、可动态编辑的倍数列表以及部分已知概率（百分比），计算剩余概率，使总概率和为 100% 且总真实收益尽量接近目标值（当无法精确满足时自动优化）。")

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
        except ValueError:
            error_msgs.append(f"倍数 {m} 的概率必须为数字")
            valid_inputs = False

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
    # 重新收集已知概率（转换为小数）
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
        st.warning(f"已知概率的加权和 {total_weighted_known:.4f} 已超过目标加权和 {target_weighted:.4f}，将尽量逼近目标。")

    remaining_p = 1 - total_p_known
    remaining_weighted = target_weighted - total_weighted_known

    # 根据未知数个数进行求解
    n_unknown = len(unknown_indices)
    p_solution = [None] * len(multipliers)  # 最终概率列表（小数）

    # 先填入已知概率
    for i, p in known_probs.items():
        p_solution[i] = p

    # 用于存储求解信息
    solve_info = ""

    if n_unknown == 0:
        if abs(remaining_p) > 1e-9 or abs(remaining_weighted) > 1e-9:
            st.error("已知概率的总和或加权和与目标不符，请检查输入")
            st.stop()
        else:
            st.success("所有概率已知，且满足条件")

    elif n_unknown == 1:
        i = unknown_indices[0]
        m = multipliers[i]
        # 理论解：p = remaining_p，必须满足 m * p = remaining_weighted
        # 若不一致，取p=remaining_p，但加权和会偏差
        p = remaining_p
        # 检查p是否在[0,1]内
        if p < 0 or p > 1:
            st.error(f"剩余概率 {p*100:.4f}% 超出 [0,100]% 范围，无法分配。")
            st.stop()
        # 计算实际加权和
        actual_weighted = m * p
        if abs(actual_weighted - remaining_weighted) > 1e-9:
            solve_info = f"注意：单个未知概率无法同时满足概率和与加权和约束，实际加权和 = {actual_weighted:.4f}，目标 = {remaining_weighted:.4f}，偏差 = {actual_weighted - remaining_weighted:.4f}。"
        p_solution[i] = p

    elif n_unknown == 2:
        i, j = unknown_indices
        m_i, m_j = multipliers[i], multipliers[j]

        # 定义在可行域内寻找最优p_i的函数
        def find_best_p(remaining_p, remaining_weighted, m_i, m_j):
            # p_i 范围 [low, high]，其中 low = max(0, remaining_p-1)，high = min(1, remaining_p)
            # 由于 remaining_p ∈ [0,1]，所以 low = 0，high = remaining_p
            low, high = 0.0, remaining_p
            # 目标函数：使 |m_i*p_i + m_j*(remaining_p - p_i) - remaining_weighted| 最小
            # 即 | (m_i - m_j)*p_i + m_j*remaining_p - remaining_weighted | 最小
            # 如果 (m_i - m_j) == 0，则加权和为常数 m_j*remaining_p，只能取任意p_i，但需检查常数是否接近目标
            if abs(m_i - m_j) < 1e-9:
                const_weighted = m_i * remaining_p
                if abs(const_weighted - remaining_weighted) < 1e-9:
                    # 任意p_i均可，取中点
                    return remaining_p / 2.0, const_weighted, 0.0
                else:
                    # 无法满足，取中点，但记录偏差
                    return remaining_p / 2.0, const_weighted, const_weighted - remaining_weighted
            else:
                # 解析解 p_i_star = (remaining_weighted - m_j*remaining_p) / (m_i - m_j)
                p_i_star = (remaining_weighted - m_j * remaining_p) / (m_i - m_j)
                if low <= p_i_star <= high:
                    # 可行，精确解
                    p_i = p_i_star
                    actual_weighted = m_i * p_i + m_j * (remaining_p - p_i)
                    return p_i, actual_weighted, 0.0
                else:
                    # 取最近的边界
                    if p_i_star < low:
                        p_i = low
                    else:
                        p_i = high
                    actual_weighted = m_i * p_i + m_j * (remaining_p - p_i)
                    return p_i, actual_weighted, actual_weighted - remaining_weighted

        p_i, actual_weighted, deviation = find_best_p(remaining_p, remaining_weighted, m_i, m_j)
        p_j = remaining_p - p_i

        # 检查是否在范围内（由函数保证）
        if p_i < 0 or p_i > 1 or p_j < 0 or p_j > 1:
            st.error(f"内部错误：计算出的概率超出 [0,1] 范围: p_i={p_i:.4f}, p_j={p_j:.4f}")
            st.stop()

        p_solution[i] = p_i
        p_solution[j] = p_j

        if abs(deviation) > 1e-9:
            solve_info = f"注意：两个未知概率无法同时满足概率和与加权和约束，实际加权和 = {actual_weighted:.4f}，目标 = {remaining_weighted:.4f}，偏差 = {deviation:.4f}。"
        else:
            solve_info = "两个未知概率精确满足约束。"

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
            "获取概率 (%)": round(prob * 100, 4),
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
    if solve_info:
        st.info(solve_info)
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
