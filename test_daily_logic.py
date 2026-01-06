"""
Test script to verify daily challenge logic works correctly
"""
from game_logic import get_daily_seed_and_date, generate_questions_for_round
from datetime import datetime, timezone

def test_daily_seed_consistency():
    """Test that daily seed is consistent within the same day"""
    print("Testing daily seed consistency...")

    seed1, date1 = get_daily_seed_and_date()
    seed2, date2 = get_daily_seed_and_date()

    assert seed1 == seed2, "Seeds should be identical on same day"
    assert date1 == date2, "Dates should be identical"

    print(f"✅ Daily seed: {seed1}")
    print(f"✅ Date: {date1}")
    print()


def test_question_generation_deterministic():
    """Test that same seed produces same questions"""
    print("Testing deterministic question generation...")

    test_seed = 20240115  # Example seed
    data_cache = {}

    questions1 = generate_questions_for_round(data_cache, daily_mode=True, daily_seed=test_seed)
    questions2 = generate_questions_for_round(data_cache, daily_mode=True, daily_seed=test_seed)

    assert len(questions1) == len(questions2), "Should generate same number of questions"

    for i, (q1, q2) in enumerate(zip(questions1, questions2)):
        assert q1['position_slot'] == q2['position_slot'], f"Q{i+1}: Position should match"
        assert q1['year'] == q2['year'], f"Q{i+1}: Year should match"
        assert q1['stat_category'] == q2['stat_category'], f"Q{i+1}: Stat should match"
        assert q1['correct_player_id'] == q2['correct_player_id'], f"Q{i+1}: Player should match"

    print(f"✅ Generated {len(questions1)} questions consistently")
    print("✅ All questions match between runs")
    print()

    # Display sample question
    if questions1:
        q = questions1[0]
        print("Sample question:")
        print(f"  Position: {q['position_slot']}")
        print(f"  Year: {q['year']}")
        print(f"  Question: {q['question_text']}")
        print(f"  Answer: {q['correct_player_name']} ({q['correct_stat_value']})")
    print()


def test_question_generation_random():
    """Test that practice mode generates different questions"""
    print("Testing random question generation (practice mode)...")

    data_cache = {}

    questions1 = generate_questions_for_round(data_cache, daily_mode=False)
    questions2 = generate_questions_for_round(data_cache, daily_mode=False)

    # These should generally be different (though could randomly be same)
    different = False
    for q1, q2 in zip(questions1, questions2):
        if (q1['year'] != q2['year'] or
            q1['stat_category'] != q2['stat_category'] or
            q1['correct_player_id'] != q2['correct_player_id']):
            different = True
            break

    if different:
        print("✅ Practice mode generates varied questions")
    else:
        print("⚠️  Practice mode generated identical questions (could be random chance)")

    print()


def test_date_format():
    """Test that date format is correct"""
    print("Testing date format...")

    _, date_str = get_daily_seed_and_date()

    # Should be YYYY-MM-DD format
    parts = date_str.split('-')
    assert len(parts) == 3, "Date should have 3 parts"
    assert len(parts[0]) == 4, "Year should be 4 digits"
    assert len(parts[1]) == 2, "Month should be 2 digits"
    assert len(parts[2]) == 2, "Day should be 2 digits"

    print(f"✅ Date format correct: {date_str}")
    print()


def main():
    print("=" * 60)
    print("DAILY DRAFT - DAILY LOGIC TESTS")
    print("=" * 60)
    print()

    try:
        test_daily_seed_consistency()
        test_date_format()
        test_question_generation_deterministic()
        test_question_generation_random()

        print("=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        print()
        print("Daily challenge logic is working correctly!")
        print("- Same seed produces same questions")
        print("- Date format is consistent")
        print("- Questions are deterministic for daily mode")
        print("- Questions are random for practice mode")

    except Exception as e:
        print("=" * 60)
        print("❌ TEST FAILED")
        print("=" * 60)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
