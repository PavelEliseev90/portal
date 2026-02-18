import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../data/repositories/rlk_repository.dart';
import '../../../data/models/rlk_model.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_text_styles.dart';
import '../widgets/rlk_card.dart';
import '../widgets/search_bar.dart';
import '../widgets/filter_dialog.dart';

final rlkRepositoryProvider = Provider((ref) => RlkRepository());

final rlkListProvider = FutureProvider.family<List<RlkModel>, String>((ref, type) async {
  final repository = ref.read(rlkRepositoryProvider);
  return await repository.getRlks(type: type);
});

final searchProvider = StateProvider<String>((ref) => '');

class RlkListScreen extends ConsumerStatefulWidget {
  const RlkListScreen({Key? key}) : super(key: key);

  @override
  ConsumerState<RlkListScreen> createState() => _RlkListScreenState();
}

class _RlkListScreenState extends ConsumerState<RlkListScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  String _currentType = '1';

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _tabController.addListener(() {
      if (_tabController.indexIsChanging) {
        setState(() {
          _currentType = _tabController.index == 0 ? '1' : '2';
        });
      }
    });
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  void _refreshList() {
    ref.invalidate(rlkListProvider(_currentType));
  }

  void _showFilterDialog() {
    showDialog(
      context: context,
      builder: (context) => FilterDialog(
        onFilterChanged: (type) {
          setState(() {
            _currentType = type;
            _tabController.animateTo(type == '1' ? 0 : 1);
          });
          _refreshList();
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final searchQuery = ref.watch(searchProvider);
    final rlksAsync = ref.watch(rlkListProvider(_currentType));

    return Scaffold(
      appBar: AppBar(
        title: const Text('Рабочие листы'),
        actions: [
          IconButton(
            icon: const Icon(Icons.filter_list),
            onPressed: _showFilterDialog,
          ),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _refreshList,
          ),
        ],
        bottom: TabBar(
          controller: _tabController,
          tabs: const [
            Tab(text: 'Продолжить оценку'),
            Tab(text: 'На согласовании'),
          ],
        ),
      ),
      body: Column(
        children: [
          // Поиск
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: SearchBarWidget(
              onSearchChanged: (query) {
                ref.read(searchProvider.notifier).state = query;
                // Здесь можно добавить фильтрацию по поисковому запросу
              },
            ),
          ),
          
          // Список RLK
          Expanded(
            child: rlksAsync.when(
              data: (rlks) {
                if (rlks.isEmpty) {
                  return Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          Icons.inbox,
                          size: 64,
                          color: Colors.grey[400],
                        ),
                        const SizedBox(height: 16),
                        Text(
                          'Нет рабочих листов',
                          style: AppTextStyles.bodySmall,
                        ),
                      ],
                    ),
                  );
                }

                // Фильтрация по поисковому запросу
                final filteredRlks = searchQuery.isEmpty
                    ? rlks
                    : rlks.where((rlk) {
                        final query = searchQuery.toLowerCase();
                        return rlk.number.toLowerCase().contains(query) ||
                            rlk.vin.toLowerCase().contains(query) ||
                            rlk.customerName.toLowerCase().contains(query) ||
                            rlk.mark.toLowerCase().contains(query) ||
                            rlk.model.toLowerCase().contains(query);
                      }).toList();

                return RefreshIndicator(
                  onRefresh: () async {
                    _refreshList();
                  },
                  child: ListView.builder(
                    itemCount: filteredRlks.length,
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    itemBuilder: (context, index) {
                      final rlk = filteredRlks[index];
                      return Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: RlkCard(
                          rlk: rlk,
                          onTap: () {
                            Navigator.of(context).pushNamed(
                              '/estimation-start',
                              arguments: rlk.id,
                            );
                          },
                        ),
                      );
                    },
                  ),
                );
              },
              loading: () => const Center(
                child: CircularProgressIndicator(),
              ),
              error: (error, stack) => Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(
                      Icons.error_outline,
                      size: 64,
                      color: AppColors.danger,
                    ),
                    const SizedBox(height: 16),
                    Text(
                      'Ошибка загрузки',
                      style: AppTextStyles.h3,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      error.toString(),
                      style: AppTextStyles.bodySmall,
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 16),
                    ElevatedButton(
                      onPressed: _refreshList,
                      child: const Text('Повторить'),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

