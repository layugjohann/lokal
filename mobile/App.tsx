import { StatusBar } from 'expo-status-bar';
import { StyleSheet, View } from 'react-native';
import LokalMapView from './src/components/LokalMapView';

export default function App(props?: { authToken?: string | null } & Record<string, unknown>) {
  return (
    <View style={styles.container}>
      <LokalMapView authToken={props?.authToken} />
      <StatusBar style="dark" />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FAF8F5',
  },
});
