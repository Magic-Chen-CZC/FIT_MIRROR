import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  SafeAreaView,
  StatusBar,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';

// Helper function to get current date in "Month Day, Year" format
const getCurrentDate = () => {
  const options: Intl.DateTimeFormatOptions = { month: 'long', day: 'numeric', year: 'numeric' };
  return new Date().toLocaleDateString('en-US', options);
};

export default function HomeScreen() {
  const userName = "CZC";
  const todaySteps = 6625;
  const goalSteps = 10000;
  const stepProgress = (todaySteps / goalSteps) * 100;

  const dailyAverageData = [
    { icon: 'heart', value: '77', unit: 'BPM', color: '#6A5ACD' },
    { icon: 'flame', value: '1800', unit: 'Kcal', color: '#FF6347' },
    { icon: 'hourglass-outline', value: '3:30', unit: 'Hrs', color: '#6A5ACD' },
    { icon: 'location-outline', value: '6.1', unit: 'Km', color: '#6A5ACD' },
  ];

  const sleepScore = 73;
  const sleepQuality = "Good";

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor={styles.container.backgroundColor} />
      <ScrollView style={styles.scrollView}>
        {/* Header */}
        <View style={styles.header}>
          <TouchableOpacity>
            <Ionicons name="menu" size={28} color="#1c1b1f" />
          </TouchableOpacity>
        </View>

        {/* Greeting */}
        <View style={styles.greetingContainer}>
          <Text style={styles.greetingText}>Hi, {userName} 👋</Text>
          <Text style={styles.dateText}>{getCurrentDate()}</Text>
        </View>

        {/* Today Steps */}
        <View style={styles.sectionContainer}>
          <Text style={styles.sectionTitle}>Today Steps</Text>
          <View style={styles.stepsProgressBarContainer}>
            <View style={[styles.stepsProgressBarFill, { width: `${stepProgress}%` }]} />
          </View>
          <View style={styles.stepsTextContainer}>
            <Text style={styles.stepsCurrent}>{todaySteps}</Text>
            <Text style={styles.stepsGoal}>/ {goalSteps}</Text>
          </View>
        </View>

        {/* Daily Average */}
        <View style={styles.sectionContainer}>
          <Text style={styles.sectionTitle}>Daily Average</Text>
          <View style={styles.dailyAverageGrid}>
            {dailyAverageData.map((item, index) => (
              <View key={index} style={styles.dailyAverageCard}>
                <Ionicons name={item.icon as any} size={24} color={item.color} />
                <Text style={styles.dailyAverageValue}>{item.value}</Text>
                <Text style={styles.dailyAverageUnit}>{item.unit}</Text>
              </View>
            ))}
          </View>
        </View>

        {/* Sleep Score */}
        <View style={styles.sectionContainer}>
          <Text style={styles.sectionTitle}>Sleep Score</Text>
          <View style={styles.sleepScoreCard}>
            <Text style={styles.sleepScoreValue}>{sleepScore}</Text>
            <View style={styles.sleepQualityBadge}>
              <Text style={styles.sleepQualityText}>{sleepQuality}</Text>
            </View>
          </View>
        </View>
        
        {/* Add some bottom padding to the scroll view content */}
        <View style={{ height: 30 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f4f4f8',
  },
  scrollView: {
    flex: 1,
    paddingHorizontal: 20,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 15,
  },
  greetingContainer: {
    marginBottom: 25,
  },
  greetingText: {
    fontSize: 26,
    fontWeight: 'bold',
    color: '#1c1b1f',
  },
  dateText: {
    fontSize: 16,
    color: '#676565',
    marginTop: 4,
  },
  sectionContainer: {
    marginBottom: 25,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#1c1b1f',
    marginBottom: 15,
  },
  stepsProgressBarContainer: {
    height: 20,
    backgroundColor: '#e0e0e0',
    borderRadius: 10,
    overflow: 'hidden',
    marginBottom: 8,
  },
  stepsProgressBarFill: {
    height: '100%',
    backgroundColor: '#6A5ACD',
    borderRadius: 10,
  },
  stepsTextContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-end',
  },
  stepsCurrent: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#6A5ACD',
  },
  stepsGoal: {
    fontSize: 16,
    color: '#333',
    alignSelf: 'flex-end',
    position: 'absolute',
    right: 10,
    bottom: -22,
  },
  dailyAverageGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  dailyAverageCard: {
    width: '48%',
    backgroundColor: '#EDE7F6',
    borderRadius: 15,
    padding: 15,
    alignItems: 'center',
    marginBottom: 15,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 1,
  },
  dailyAverageValue: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#1c1b1f',
    marginTop: 8,
  },
  dailyAverageUnit: {
    fontSize: 14,
    color: '#555',
    marginTop: 2,
  },
  sleepScoreCard: {
    backgroundColor: '#EDE7F6',
    borderRadius: 15,
    padding: 20,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 1,
  },
  sleepScoreValue: {
    fontSize: 48,
    fontWeight: 'bold',
    color: '#1c1b1f',
  },
  sleepQualityBadge: {
    backgroundColor: '#6A5ACD',
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 5,
    marginTop: 10,
  },
  sleepQualityText: {
    fontSize: 14,
    fontWeight: 'bold',
    color: 'white',
  },
});